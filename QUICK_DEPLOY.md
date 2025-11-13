# Quick Deployment Checklist

## 🚀 5-Minute Deployment Guide

### Step 1: MongoDB Atlas (2 minutes)
- [ ] Sign up at https://www.mongodb.com/cloud/atlas
- [ ] Create free cluster
- [ ] Create database user
- [ ] Whitelist IP (0.0.0.0/0)
- [ ] Copy connection string: `mongodb+srv://user:pass@cluster.mongodb.net/visual_product_matcher`

### Step 2: Backend - Render (2 minutes)
- [ ] Sign up at https://render.com
- [ ] Click "New +" → "Web Service"
- [ ] Connect GitHub repo: `Vijaykumar830/VisualproductMatcher`
- [ ] Settings:
  - Root Directory: `backend`
  - Build: `pip install -r requirements.txt`
  - Start: `uvicorn server:app --host 0.0.0.0 --port $PORT`
- [ ] Environment Variables:
  - `MONGO_URL`: (your MongoDB connection string)
  - `DB_NAME`: `visual_product_matcher`
  - `CORS_ORIGINS`: `*`
- [ ] Deploy and copy URL: `https://your-app.onrender.com`

### Step 3: Frontend - Vercel (1 minute)
- [ ] Sign up at https://vercel.com
- [ ] "Add New Project" → Import GitHub repo
- [ ] Settings:
  - Root Directory: `frontend`
  - Framework: Create React App
  - Build: `npm run build`
- [ ] Environment Variable:
  - `REACT_APP_BACKEND_URL`: (your Render backend URL)
- [ ] Deploy and copy URL: `https://your-app.vercel.app`

### Step 4: Update CORS
- [ ] Go back to Render
- [ ] Update `CORS_ORIGINS` to your Vercel URL
- [ ] Redeploy backend

### Done! 🎉
Your app is live at: `https://your-app.vercel.app`

---

## 📝 Important Notes

1. **Render Free Tier**: Spins down after 15 min inactivity (first request takes 30-60s)
2. **MongoDB Atlas**: 512MB free storage (enough for development)
3. **Vercel**: Unlimited deployments, fast CDN
4. **All services are FREE** - $0/month cost

---

## 🔧 Troubleshooting

**Backend not connecting?**
- Check MongoDB connection string
- Verify IP whitelist in Atlas
- Check Render logs

**Frontend API errors?**
- Verify `REACT_APP_BACKEND_URL` in Vercel
- Check CORS settings in backend
- Test backend URL directly: `https://your-backend.onrender.com/api/`

**CLIP model issues?**
- Render free tier has limited memory
- Model may take time to load on first request
- Consider using a paid tier for production

---

For detailed instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md)

