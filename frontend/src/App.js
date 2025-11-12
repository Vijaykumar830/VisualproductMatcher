import { useState, useEffect } from "react";
import "@/App.css";
import axios from "axios";
import { Upload, Link as LinkIcon, Search, SlidersHorizontal, X, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { toast } from "sonner";
import { Toaster } from "@/components/ui/sonner";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [searchMode, setSearchMode] = useState("upload"); // upload or url
  const [selectedFile, setSelectedFile] = useState(null);
  const [imageUrl, setImageUrl] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [minSimilarity, setMinSimilarity] = useState(0.5);
  const [resultLimit, setResultLimit] = useState(10);
  const [showFilters, setShowFilters] = useState(false);
  const [isSeeding, setIsSeeding] = useState(false);
  const [productsCount, setProductsCount] = useState(0);

  useEffect(() => {
    loadCategories();
    checkProducts();
  }, []);

  const loadCategories = async () => {
    try {
      const response = await axios.get(`${API}/products/categories`);
      setCategories(response.data.categories);
    } catch (error) {
      console.error("Failed to load categories:", error);
    }
  };

  const checkProducts = async () => {
    try {
      const response = await axios.get(`${API}/products`);
      setProductsCount(response.data.length);
    } catch (error) {
      console.error("Failed to check products:", error);
    }
  };

  const seedDatabase = async () => {
    setIsSeeding(true);
    try {
      const response = await axios.get(`${API}/seed-products`);
      toast.success(response.data.message);
      await loadCategories();
      await checkProducts();
    } catch (error) {
      toast.error("Failed to seed database");
    } finally {
      setIsSeeding(false);
    }
  };

  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.startsWith("image/")) {
        toast.error("Please select an image file");
        return;
      }
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
      setResults([]);
    }
  };

  const handleUrlChange = (e) => {
    const url = e.target.value;
    setImageUrl(url);
    if (url) {
      setPreviewUrl(url);
      setResults([]);
    }
  };

  const handleSearch = async () => {
    if (searchMode === "upload" && !selectedFile) {
      toast.error("Please select an image to upload");
      return;
    }
    if (searchMode === "url" && !imageUrl) {
      toast.error("Please enter an image URL");
      return;
    }

    setLoading(true);
    try {
      let response;
      const formData = new FormData();

      if (searchMode === "upload") {
        formData.append("file", selectedFile);
        formData.append("limit", resultLimit);
        formData.append("min_similarity", minSimilarity);
        if (selectedCategory !== "all") {
          formData.append("category", selectedCategory);
        }
        response = await axios.post(`${API}/search/upload`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      } else {
        formData.append("url", imageUrl);
        formData.append("limit", resultLimit);
        formData.append("min_similarity", minSimilarity);
        if (selectedCategory !== "all") {
          formData.append("category", selectedCategory);
        }
        response = await axios.post(`${API}/search/url`, formData);
      }

      setResults(response.data);
      if (response.data.length === 0) {
        toast.info("No similar products found. Try adjusting the similarity threshold.");
      } else {
        toast.success(`Found ${response.data.length} similar products`);
      }
    } catch (error) {
      console.error("Search error:", error);
      toast.error("Search failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const clearSearch = () => {
    setSelectedFile(null);
    setImageUrl("");
    setPreviewUrl("");
    setResults([]);
  };

  return (
    <div className="App">
      <Toaster position="top-center" richColors />
      
      {/* Hero Section */}
      <div className="hero-section">
        <div className="hero-content">
          <h1 className="hero-title" data-testid="app-title">
            Visual Product Matcher
          </h1>
          <p className="hero-subtitle" data-testid="app-subtitle">
            Find visually similar products using AI-powered image search
          </p>
          
          {productsCount === 0 && (
            <div className="seed-banner" data-testid="seed-banner">
              <p>Database is empty. Load sample products to get started.</p>
              <Button
                onClick={seedDatabase}
                disabled={isSeeding}
                className="seed-button"
                data-testid="seed-database-button"
              >
                {isSeeding ? (
                  <><Loader2 className="animate-spin mr-2" size={16} /> Loading Products...</>
                ) : (
                  "Load 50+ Sample Products"
                )}
              </Button>
            </div>
          )}
        </div>
      </div>

      {/* Search Section */}
      <div className="search-container">
        <div className="search-card">
          {/* Search Mode Tabs */}
          <div className="search-tabs" data-testid="search-tabs">
            <button
              className={`tab ${searchMode === "upload" ? "active" : ""}`}
              onClick={() => {
                setSearchMode("upload");
                clearSearch();
              }}
              data-testid="upload-tab"
            >
              <Upload size={18} />
              Upload Image
            </button>
            <button
              className={`tab ${searchMode === "url" ? "active" : ""}`}
              onClick={() => {
                setSearchMode("url");
                clearSearch();
              }}
              data-testid="url-tab"
            >
              <LinkIcon size={18} />
              Image URL
            </button>
          </div>

          {/* Upload/URL Input */}
          <div className="search-input-section">
            {searchMode === "upload" ? (
              <div className="upload-area">
                <input
                  type="file"
                  id="file-upload"
                  accept="image/*"
                  onChange={handleFileSelect}
                  className="file-input"
                  data-testid="file-input"
                />
                <label htmlFor="file-upload" className="upload-label" data-testid="upload-label">
                  <Upload size={32} />
                  <span>Click to upload or drag and drop</span>
                  <span className="upload-hint">PNG, JPG, WEBP up to 10MB</span>
                </label>
              </div>
            ) : (
              <div className="url-input-wrapper">
                <Label htmlFor="image-url">Image URL</Label>
                <Input
                  id="image-url"
                  type="url"
                  placeholder="https://example.com/image.jpg"
                  value={imageUrl}
                  onChange={handleUrlChange}
                  data-testid="url-input"
                />
              </div>
            )}
          </div>

          {/* Preview */}
          {previewUrl && (
            <div className="preview-section" data-testid="preview-section">
              <div className="preview-header">
                <span>Preview</span>
                <button onClick={clearSearch} className="clear-button" data-testid="clear-preview-button">
                  <X size={16} />
                </button>
              </div>
              <img src={previewUrl} alt="Preview" className="preview-image" data-testid="preview-image" />
            </div>
          )}

          {/* Filters */}
          <div className="filters-section">
            <button
              onClick={() => setShowFilters(!showFilters)}
              className="filters-toggle"
              data-testid="filters-toggle"
            >
              <SlidersHorizontal size={18} />
              {showFilters ? "Hide Filters" : "Show Filters"}
            </button>

            {showFilters && (
              <div className="filters-content" data-testid="filters-content">
                <div className="filter-group">
                  <Label>Category</Label>
                  <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                    <SelectTrigger data-testid="category-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Categories</SelectItem>
                      {categories.map((cat) => (
                        <SelectItem key={cat} value={cat}>
                          {cat}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="filter-group">
                  <Label>Similarity Threshold: {minSimilarity.toFixed(2)}</Label>
                  <Slider
                    value={[minSimilarity]}
                    onValueChange={(val) => setMinSimilarity(val[0])}
                    min={0.1}
                    max={1}
                    step={0.05}
                    data-testid="similarity-slider"
                  />
                </div>

                <div className="filter-group">
                  <Label>Result Limit: {resultLimit}</Label>
                  <Slider
                    value={[resultLimit]}
                    onValueChange={(val) => setResultLimit(val[0])}
                    min={5}
                    max={50}
                    step={5}
                    data-testid="limit-slider"
                  />
                </div>
              </div>
            )}
          </div>

          {/* Search Button */}
          <Button
            onClick={handleSearch}
            disabled={loading || (!selectedFile && !imageUrl)}
            className="search-button"
            data-testid="search-button"
          >
            {loading ? (
              <>
                <Loader2 className="animate-spin mr-2" size={18} />
                Searching...
              </>
            ) : (
              <>
                <Search size={18} className="mr-2" />
                Find Similar Products
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Results Section */}
      {results.length > 0 && (
        <div className="results-container" data-testid="results-container">
          <h2 className="results-title">Similar Products ({results.length})</h2>
          <div className="results-grid">
            {results.map((product, index) => (
              <Card key={product.id} className="product-card" data-testid={`product-card-${index}`}>
                <CardContent className="product-content">
                  <div className="product-image-wrapper">
                    <img
                      src={product.image_url}
                      alt={product.name}
                      className="product-image"
                      data-testid={`product-image-${index}`}
                    />
                    <div className="similarity-badge" data-testid={`similarity-score-${index}`}>
                      {(product.similarity_score * 100).toFixed(0)}% Match
                    </div>
                  </div>
                  <div className="product-info">
                    <h3 className="product-name" data-testid={`product-name-${index}`}>{product.name}</h3>
                    <p className="product-category" data-testid={`product-category-${index}`}>{product.category}</p>
                    {product.price && (
                      <p className="product-price" data-testid={`product-price-${index}`}>${product.price}</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="footer">
        <p>Built with OpenAI CLIP & FastAPI</p>
        <p className="footer-stats" data-testid="products-count">{productsCount} products in database</p>
      </footer>
    </div>
  );
}

export default App;