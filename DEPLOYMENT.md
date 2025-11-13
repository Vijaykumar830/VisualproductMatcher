# Deployment Guide - Visual Product Matcher

This guide will help you deploy both the frontend and backend for free using:
- **Backend**: Render.com (Free Tier)
- **Frontend**: Vercel (Free Tier)
- **Database**: MongoDB Atlas (Free Tier)

## Prerequisites

1. GitHub account (for connecting repositories)
2. Render.com account (sign up at https://render.com)
3. Vercel account (sign up at https://vercel.com)
4. MongoDB Atlas account (sign up at https://www.mongodb.com/cloud/atlas)

---

## Step 1: Set Up MongoDB Atlas (Database)

1. Go to https://www.mongodb.com/cloud/atlas
2. Sign up for a free account
3. Create a new cluster (choose the FREE tier)
4. Create a database user:
   - Go to "Database Access" → "Add New Database User"
   - Choose "Password" authentication
   - Save the username and password
5. Whitelist IP addresses:
   - Go to "Network Access" → "Add IP Address"
   - Click "Allow Access from Anywhere" (0.0.0.0/0) for development
6. Get your connection string:
   - Go to "Database" → "Connect"
   - Choose "Connect your application"
   - Copy the connection string (it looks like: `mongodb+srv://username:password@cluster.mongodb.net/`)
   - Replace `<password>` with your database password
   - Replace `<dbname>` with `visual_product_matcher`

**Save this connection string - you'll need it for the backend deployment!**

---

## Step 2: Deploy Backend to Render.com

### 2.1 Prepare Your Repository

1. Make sure your code is pushed to GitHub
2. The backend folder should have:
   - `server.py`
   - `requirements.txt`
   - `Procfile` (already created)
   - `runtime.txt` (already created)

### 2.2 Deploy on Render

1. Go to https://dashboard.render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Select your repository: `Vijaykumar830/VisualproductMatcher`
5. Configure the service:
   - **Name**: `visual-product-matcher-backend` (or any name you prefer)
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
6. Add Environment Variables:
   - `MONGO_URL`: Your MongoDB Atlas connection string
   - `DB_NAME`: `visual_product_matcher`
   - `CORS_ORIGINS`: `*` (or your frontend URL after deployment)
   - `PORT`: (Render sets this automatically, but you can add it)
7. Click "Create Web Service"
8. Wait for deployment (5-10 minutes for first deployment)
9. **Copy your backend URL** (e.g., `https://visual-product-matcher-backend.onrender.com`)

**Note**: Free tier on Render spins down after 15 minutes of inactivity. First request after spin-down may take 30-60 seconds.

---

## Step 3: Deploy Frontend to Vercel

### 3.1 Prepare Frontend

1. Make sure your code is pushed to GitHub
2. The frontend folder should have:
   - `package.json`
   - `vercel.json` (already created)

### 3.2 Deploy on Vercel

1. Go to https://vercel.com
2. Sign in with GitHub
3. Click "Add New Project"
4. Import your repository: `Vijaykumar830/VisualproductMatcher`
5. Configure the project:
   - **Framework Preset**: Create React App
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build` (or `yarn build`)
   - **Output Directory**: `build`
6. Add Environment Variables:
   - `REACT_APP_BACKEND_URL`: Your Render backend URL (e.g., `https://visual-product-matcher-backend.onrender.com`)
7. Click "Deploy"
8. Wait for deployment (2-5 minutes)
9. **Copy your frontend URL** (e.g., `https://visual-product-matcher.vercel.app`)

### 3.3 Update CORS in Backend

After getting your frontend URL, update the backend CORS settings:

1. Go back to Render dashboard
2. Select your backend service
3. Go to "Environment" tab
4. Update `CORS_ORIGINS` to your Vercel frontend URL:
   - Example: `https://visual-product-matcher.vercel.app`
   - Or keep `*` for development (not recommended for production)
5. Save and redeploy

---

## Step 4: Update Frontend Backend URL

1. Go to Vercel dashboard
2. Select your project
3. Go to "Settings" → "Environment Variables"
4. Update `REACT_APP_BACKEND_URL` if needed
5. Redeploy if necessary

---

## Step 5: Test Your Deployment

1. Visit your frontend URL
2. Try uploading an image or using image URL search
3. Check backend logs in Render dashboard if there are issues

---

## Alternative: Deploy Both on Render

If you prefer to use Render for both:

### Frontend on Render (Static Site)

1. In Render, create a "Static Site"
2. Root Directory: `frontend`
3. Build Command: `npm install && npm run build`
4. Publish Directory: `build`
5. Add environment variable: `REACT_APP_BACKEND_URL`

---

## Troubleshooting

### Backend Issues

- **CLIP model not loading**: Render free tier has limited memory. The model may take time to load.
- **MongoDB connection errors**: Check your connection string and IP whitelist
- **CORS errors**: Make sure `CORS_ORIGINS` includes your frontend URL

### Frontend Issues

- **API calls failing**: Check `REACT_APP_BACKEND_URL` environment variable
- **Build errors**: Check Vercel build logs
- **404 errors**: Make sure `vercel.json` routes are configured correctly

### Database Issues

- **Connection timeout**: Check MongoDB Atlas IP whitelist
- **Authentication errors**: Verify database username and password

---

## Environment Variables Summary

### Backend (Render)
```
MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/visual_product_matcher
DB_NAME=visual_product_matcher
CORS_ORIGINS=https://your-frontend-url.vercel.app
PORT=10000 (auto-set by Render)
```

### Frontend (Vercel)
```
REACT_APP_BACKEND_URL=https://your-backend-url.onrender.com
```

---

## Free Tier Limitations

### Render
- 750 hours/month free (enough for 24/7 operation)
- Spins down after 15 minutes of inactivity
- 512MB RAM
- Slow cold starts (30-60 seconds)

### Vercel
- Unlimited deployments
- 100GB bandwidth/month
- Fast CDN
- No cold starts

### MongoDB Atlas
- 512MB storage
- Shared cluster
- Sufficient for development and small projects

---

## Cost

**Total Cost: $0/month** (all services are free tier)

---

## Next Steps

1. Set up custom domains (optional, may have costs)
2. Set up monitoring and alerts
3. Configure CI/CD for automatic deployments
4. Set up error tracking (Sentry free tier)

---

## Support

If you encounter issues:
1. Check service logs (Render/Vercel dashboards)
2. Verify environment variables
3. Test API endpoints directly
4. Check MongoDB Atlas connection status

Good luck with your deployment! 🚀

