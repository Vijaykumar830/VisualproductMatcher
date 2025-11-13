from fastapi import FastAPI, APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, HttpUrl
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import io
from PIL import Image
import requests
import numpy as np
import base64

try:
    from transformers import CLIPModel, CLIPProcessor
    import torch
    CLIP_AVAILABLE = True
except ImportError:
    CLIP_AVAILABLE = False
    print("CLIP not available - install transformers and torch")

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('DB_NAME', 'visual_product_matcher')
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# Create the main app without a prefix
app = FastAPI(title="Visual Product Matcher", description="Find visually similar products")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Upload directory
UPLOAD_DIR = Path(ROOT_DIR) / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Initialize CLIP model
class CLIPEmbedder:
    def __init__(self):
        if not CLIP_AVAILABLE:
            raise Exception("CLIP not available")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        self.model.eval()
    
    def get_image_embedding(self, image):
        with torch.no_grad():
            inputs = self.processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            outputs = self.model.get_image_features(**inputs)
            embedding = torch.nn.functional.normalize(outputs, p=2, dim=1)
        return embedding.cpu().numpy().flatten()

# Global embedder instance
embedder = None
if CLIP_AVAILABLE:
    try:
        embedder = CLIPEmbedder()
        logging.info("CLIP model loaded successfully")
    except Exception as e:
        logging.error(f"Failed to load CLIP model: {e}")

# Define Models
class Product(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    category: str
    image_url: str
    price: Optional[float] = None
    description: Optional[str] = None
    embedding: List[float] = []
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ProductCreate(BaseModel):
    name: str
    category: str
    image_url: str
    price: Optional[float] = None
    description: Optional[str] = None

class SimilarProduct(BaseModel):
    id: str
    name: str
    category: str
    image_url: str
    price: Optional[float] = None
    description: Optional[str] = None
    similarity_score: float

class SearchRequest(BaseModel):
    limit: int = 10
    min_similarity: float = 0.5
    category: Optional[str] = None

# Utility functions
def load_image_from_url(url: str) -> Image.Image:
    """Load image from URL."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert('RGB')
        return image
    except Exception as e:
        raise ValueError(f"Failed to load image from URL: {str(e)}")

def load_image_from_bytes(image_bytes: bytes) -> Image.Image:
    """Load image from bytes."""
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        return image
    except Exception as e:
        raise ValueError(f"Failed to load image: {str(e)}")

def calculate_cosine_similarity(emb1: List[float], emb2: List[float]) -> float:
    """Calculate cosine similarity between two embeddings."""
    return float(np.dot(emb1, emb2))

# Routes
@api_router.get("/")
async def root():
    return {"message": "Visual Product Matcher API", "clip_available": CLIP_AVAILABLE}

@api_router.post("/products", response_model=Product)
async def create_product(product: ProductCreate):
    """Create a new product with embedding."""
    if not embedder:
        raise HTTPException(status_code=503, detail="CLIP model not available")
    
    try:
        # Load image and generate embedding
        image = load_image_from_url(product.image_url)
        embedding = embedder.get_image_embedding(image)
        
        # Create product document
        product_dict = product.model_dump()
        product_obj = Product(**product_dict, embedding=embedding.tolist())
        
        # Store in database
        doc = product_obj.model_dump()
        doc['created_at'] = doc['created_at'].isoformat()
        
        await db.products.insert_one(doc)
        return product_obj
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating product: {str(e)}")

@api_router.get("/products", response_model=List[Product])
async def get_products():
    """Get all products."""
    products = await db.products.find({}, {"_id": 0}).to_list(1000)
    for product in products:
        if isinstance(product['created_at'], str):
            product['created_at'] = datetime.fromisoformat(product['created_at'])
    return products

@api_router.get("/products/categories")
async def get_categories():
    """Get all unique categories."""
    categories = await db.products.distinct("category")
    return {"categories": categories}

@api_router.post("/search/upload", response_model=List[SimilarProduct])
async def search_by_upload(
    file: UploadFile = File(...),
    limit: int = Form(10),
    min_similarity: float = Form(0.3),
    category: Optional[str] = Form(None)
):
    """Search for similar products using uploaded image."""
    if not embedder:
        raise HTTPException(status_code=503, detail="CLIP model not available")
    
    try:
        # Read and process image
        file_content = await file.read()
        image = load_image_from_bytes(file_content)
        query_embedding = embedder.get_image_embedding(image)
        
        # Search in database
        filter_query = {} if not category else {"category": category}
        products = await db.products.find(filter_query, {"_id": 0}).to_list(1000)
        
        # Calculate similarities
        results = []
        for product in products:
            if product.get('embedding'):
                similarity = calculate_cosine_similarity(
                    query_embedding.tolist(),
                    product['embedding']
                )
                if similarity >= min_similarity:
                    results.append({
                        "id": product['id'],
                        "name": product['name'],
                        "category": product['category'],
                        "image_url": product['image_url'],
                        "price": product.get('price'),
                        "description": product.get('description'),
                        "similarity_score": similarity
                    })
        
        # Sort by similarity
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:limit]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching: {str(e)}")

@api_router.post("/search/url", response_model=List[SimilarProduct])
async def search_by_url(url: str = Form(...), limit: int = Form(10),
                       min_similarity: float = Form(0.3),
                       category: Optional[str] = Form(None)):
    """Search for similar products using image URL."""
    if not embedder:
        raise HTTPException(status_code=503, detail="CLIP model not available")
    
    try:
        # Load image from URL
        image = load_image_from_url(url)
        query_embedding = embedder.get_image_embedding(image)
        
        # Search in database
        filter_query = {} if not category else {"category": category}
        products = await db.products.find(filter_query, {"_id": 0}).to_list(1000)
        
        # Calculate similarities
        results = []
        for product in products:
            if product.get('embedding'):
                similarity = calculate_cosine_similarity(
                    query_embedding.tolist(),
                    product['embedding']
                )
                if similarity >= min_similarity:
                    results.append({
                        "id": product['id'],
                        "name": product['name'],
                        "category": product['category'],
                        "image_url": product['image_url'],
                        "price": product.get('price'),
                        "description": product.get('description'),
                        "similarity_score": similarity
                    })
        
        # Sort by similarity
        results.sort(key=lambda x: x['similarity_score'], reverse=True)
        return results[:limit]
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching: {str(e)}")

@api_router.get("/seed-products")
async def seed_products():
    """Seed database with sample products."""
    if not embedder:
        raise HTTPException(status_code=503, detail="CLIP model not available")
    
    # Check if already seeded
    count = await db.products.count_documents({})
    if count > 0:
        return {"message": f"Database already contains {count} products"}
    
    # Sample product data (50+ products)
    sample_products = [
        # Electronics - Laptops
        {"name": "MacBook Pro 16", "category": "Electronics", "price": 2499, "image_url": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=500"},
        {"name": "Dell XPS 15", "category": "Electronics", "price": 1899, "image_url": "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=500"},
        {"name": "HP Spectre x360", "category": "Electronics", "price": 1599, "image_url": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=500"},
        {"name": "Lenovo ThinkPad", "category": "Electronics", "price": 1299, "image_url": "https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=500"},
        {"name": "ASUS ROG Gaming Laptop", "category": "Electronics", "price": 1799, "image_url": "https://images.unsplash.com/photo-1603302576837-37561b2e2302?w=500"},
        
        # Electronics - Phones
        {"name": "iPhone 15 Pro", "category": "Electronics", "price": 999, "image_url": "https://images.unsplash.com/photo-1592286927505-0485968717fc?w=500"},
        {"name": "Samsung Galaxy S24", "category": "Electronics", "price": 899, "image_url": "https://images.unsplash.com/photo-1610945415295-d9bbf067e59c?w=500"},
        {"name": "Google Pixel 8", "category": "Electronics", "price": 799, "image_url": "https://images.unsplash.com/photo-1598327105666-5b89351aff97?w=500"},
        {"name": "OnePlus 12", "category": "Electronics", "price": 699, "image_url": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=500"},
        
        # Fashion - Shoes
        {"name": "Nike Air Max", "category": "Fashion", "price": 150, "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500"},
        {"name": "Adidas Ultraboost", "category": "Fashion", "price": 180, "image_url": "https://images.unsplash.com/photo-1608231387042-66d1773070a5?w=500"},
        {"name": "Converse Chuck Taylor", "category": "Fashion", "price": 65, "image_url": "https://images.unsplash.com/photo-1607522370275-f14206abe5d3?w=500"},
        {"name": "Vans Old Skool", "category": "Fashion", "price": 70, "image_url": "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=500"},
        {"name": "Puma RS-X", "category": "Fashion", "price": 110, "image_url": "https://images.unsplash.com/photo-1606107557195-0e29a4b5b4aa?w=500"},
        
        # Fashion - Clothing
        {"name": "Leather Jacket", "category": "Fashion", "price": 299, "image_url": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=500"},
        {"name": "Denim Jacket", "category": "Fashion", "price": 89, "image_url": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=500"},
        {"name": "Hoodie Sweatshirt", "category": "Fashion", "price": 59, "image_url": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=500"},
        {"name": "T-Shirt Pack", "category": "Fashion", "price": 29, "image_url": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=500"},
        
        # Furniture - Chairs
        {"name": "Office Chair Ergonomic", "category": "Furniture", "price": 349, "image_url": "https://images.unsplash.com/photo-1580480055273-228ff5388ef8?w=500"},
        {"name": "Gaming Chair", "category": "Furniture", "price": 299, "image_url": "https://images.unsplash.com/photo-1598550476439-6847785fcea6?w=500"},
        {"name": "Wooden Dining Chair", "category": "Furniture", "price": 129, "image_url": "https://images.unsplash.com/photo-1503602642458-232111445657?w=500"},
        {"name": "Recliner Armchair", "category": "Furniture", "price": 599, "image_url": "https://images.unsplash.com/photo-1567538096630-e0c55bd6374c?w=500"},
        
        # Furniture - Tables
        {"name": "Coffee Table Modern", "category": "Furniture", "price": 199, "image_url": "https://images.unsplash.com/photo-1618219740975-d40978bb7378?w=500"},
        {"name": "Dining Table Wood", "category": "Furniture", "price": 799, "image_url": "https://images.unsplash.com/photo-1617806118233-18e1de247200?w=500"},
        {"name": "Standing Desk", "category": "Furniture", "price": 449, "image_url": "https://images.unsplash.com/photo-1595515106969-1ce29566ff1c?w=500"},
        
        # Home - Decor
        {"name": "Table Lamp Modern", "category": "Home", "price": 79, "image_url": "https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=500"},
        {"name": "Wall Mirror Large", "category": "Home", "price": 149, "image_url": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?w=500"},
        {"name": "Throw Pillows Set", "category": "Home", "price": 39, "image_url": "https://images.unsplash.com/photo-1584100936595-c0654b55a2e2?w=500"},
        {"name": "Area Rug", "category": "Home", "price": 199, "image_url": "https://images.unsplash.com/photo-1600166898405-da9535204843?w=500"},
        {"name": "Wall Art Canvas", "category": "Home", "price": 89, "image_url": "https://images.unsplash.com/photo-1513519245088-0e12902e35ca?w=500"},
        
        # Sports - Equipment
        {"name": "Yoga Mat Premium", "category": "Sports", "price": 49, "image_url": "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=500"},
        {"name": "Dumbbell Set", "category": "Sports", "price": 199, "image_url": "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?w=500"},
        {"name": "Tennis Racket", "category": "Sports", "price": 159, "image_url": "https://images.unsplash.com/photo-1617083278810-f9de9086e4f9?w=500"},
        {"name": "Basketball Wilson", "category": "Sports", "price": 29, "image_url": "https://images.unsplash.com/photo-1546519638-68e109498ffc?w=500"},
        {"name": "Running Shoes Pro", "category": "Sports", "price": 139, "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500"},
        
        # Books
        {"name": "Programming Books Set", "category": "Books", "price": 79, "image_url": "https://images.unsplash.com/photo-1589998059171-988d887df646?w=500"},
        {"name": "Fiction Novel Collection", "category": "Books", "price": 49, "image_url": "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=500"},
        {"name": "Coffee Table Book", "category": "Books", "price": 39, "image_url": "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=500"},
        
        # Kitchen
        {"name": "Blender High Speed", "category": "Kitchen", "price": 99, "image_url": "https://images.unsplash.com/photo-1570222094114-d054a817e56b?w=500"},
        {"name": "Coffee Maker", "category": "Kitchen", "price": 129, "image_url": "https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6?w=500"},
        {"name": "Knife Set Professional", "category": "Kitchen", "price": 149, "image_url": "https://images.unsplash.com/photo-1593618998160-e34014e67546?w=500"},
        {"name": "Cookware Set", "category": "Kitchen", "price": 199, "image_url": "https://images.unsplash.com/photo-1556911220-bff31c812dba?w=500"},
        
        # Accessories
        {"name": "Smartwatch", "category": "Accessories", "price": 299, "image_url": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=500"},
        {"name": "Sunglasses Ray-Ban", "category": "Accessories", "price": 159, "image_url": "https://images.unsplash.com/photo-1511499767150-a48a237f0083?w=500"},
        {"name": "Backpack Leather", "category": "Accessories", "price": 189, "image_url": "https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=500"},
        {"name": "Wallet Bifold", "category": "Accessories", "price": 49, "image_url": "https://images.unsplash.com/photo-1627123424574-724758594e93?w=500"},
        {"name": "Belt Designer", "category": "Accessories", "price": 79, "image_url": "https://images.unsplash.com/photo-1624222247344-550fb60583aa?w=500"},
        
        # Electronics - Audio
        {"name": "Wireless Headphones", "category": "Electronics", "price": 249, "image_url": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500"},
        {"name": "Bluetooth Speaker", "category": "Electronics", "price": 99, "image_url": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=500"},
        {"name": "Earbuds Wireless", "category": "Electronics", "price": 129, "image_url": "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=500"},
        
        # Beauty
        {"name": "Skincare Set", "category": "Beauty", "price": 89, "image_url": "https://images.unsplash.com/photo-1556228720-195a672e8a03?w=500"},
        {"name": "Makeup Palette", "category": "Beauty", "price": 59, "image_url": "https://images.unsplash.com/photo-1596704017254-9b121068ec31?w=500"},
        {"name": "Hair Dryer Professional", "category": "Beauty", "price": 149, "image_url": "https://images.unsplash.com/photo-1522338242992-e1a54906a8da?w=500"},
    ]
    
    inserted = 0
    failed = 0
    
    for product_data in sample_products:
        try:
            # Load image and generate embedding
            image = load_image_from_url(product_data['image_url'])
            embedding = embedder.get_image_embedding(image)
            
            # Create product
            product = Product(
                name=product_data['name'],
                category=product_data['category'],
                image_url=product_data['image_url'],
                price=product_data['price'],
                embedding=embedding.tolist()
            )
            
            doc = product.model_dump()
            doc['created_at'] = doc['created_at'].isoformat()
            await db.products.insert_one(doc)
            inserted += 1
            
        except Exception as e:
            logging.error(f"Failed to add product {product_data['name']}: {e}")
            failed += 1
    
    return {
        "message": f"Seeded {inserted} products successfully",
        "inserted": inserted,
        "failed": failed
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()