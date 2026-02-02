# Quick Start Guide - Premium Tenant Management Dashboard

## 🚀 Installation & Setup

### Step 1: Install Dependencies

```bash
# Navigate to frontend directory
cd frontend

# Install all packages (Framer Motion, date-fns, Heroicons, etc.)
npm install
```

### Step 2: Start Backend Server

```bash
# Open a new terminal
cd backend

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Start FastAPI server
uvicorn app.main:app --reload
```

✅ Backend should be running at `http://localhost:8000`

### Step 3: Start Frontend

```bash
# In the frontend directory
npm run dev
```

✅ Frontend should open at `http://localhost:5173`

---

## 📋 What to Expect

### Dashboard Features
- **Dark Theme**: Cinematic UI with warm orange accents
- **Complaints Overview**: Grid of complaint cards with stats
- **Calendar View**: Monthly view with complaint indicators
- **Real-Time Updates**: Auto-refresh every 30 seconds
- **Filters**: By status and priority
- **Smooth Animations**: Fade-in effects and hover interactions

### First Time Setup
1. The dashboard will attempt to fetch complaints from the backend
2. If backend is not running, you'll see an error banner
3. Once backend is connected, complaints will load automatically
4. Use filters to narrow down the view
5. Click on status dropdowns to update complaint status
6. Navigate to Calendar view to see complaints by date

---

## 🎨 Design Language

Matches the LeadPipe aesthetic:
- Near-black backgrounds (#0a0a0a, #171717)
- Warm orange accents (#ff6b35)
- Modern fonts: Outfit + Space Grotesk
- High contrast text
- Glowing hover effects

---

## 🛠 Troubleshooting

**Issue**: `npm: command not found`
- **Solution**: Install Node.js from [nodejs.org](https://nodejs.org)

**Issue**: Backend not responding
- **Solution**: Make sure backend is running on port 8000
- Check: `curl http://localhost:8000/`

**Issue**: CORS errors in browser console
- **Solution**: Backend `.env` already has CORS enabled for `localhost:5173`

**Issue**: Complaints not loading
- **Solution**: 
  1. Check backend is running
  2. Open browser console for errors
  3. Verify backend has complaints in database

---

## 📦 Dependencies Overview

```json
{
  "framer-motion": "^11.0.0",     // Smooth animations
  "date-fns": "^3.0.0",           // Calendar date handling
  "@heroicons/react": "^2.1.0"    // Professional icons
}
```

---

## 🎯 Next Steps

1. **Add Sample Data**: Create test complaints via backend API or Vapi voice calls
2. **Test Filters**: Try filtering by status and priority
3. **Test Calendar**: Click on dates to see complaints
4. **Update Statuses**: Change complaint status via dropdown
5. **Customize**: Modify colors in `index.css` CSS custom properties

---

## 📞 Support

If you encounter issues:
1. Check backend logs for API errors
2. Check browser console for frontend errors
3. Ensure all dependencies are installed (`npm install`)
4. Verify backend database has data
