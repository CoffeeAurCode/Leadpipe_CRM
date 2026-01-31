# Manager Dashboard - React Frontend

A React-based dashboard for building managers to view and manage tenant complaints in real-time.

## Features

- 📊 **Real-time Complaint Monitoring** - View all complaints in a scrollable table
- 🔄 **Auto-refresh** - Dashboard updates every 5 seconds automatically
- ✏️ **Editable Status** - Update complaint status with dropdown (pending, in-progress, resolved, closed)
- 🎨 **Priority Visual Indicators** - Color-coded rows based on priority:
  - 🔴 High priority → Red
  - 🟡 Medium priority → Yellow
  - 🔵 Low priority → Blue
- 📱 **Mobile Number Display** - Shows phone numbers from CallLog when available
- 🎯 **Modern UI** - Clean, professional design with smooth animations

## Prerequisites

- Node.js (v16 or higher)
- npm or yarn
- Backend API running on `http://localhost:8000`

## Installation

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

## Running the Application

1. **Start the backend first** (from the backend directory):
```bash
cd ../backend
python -u -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

2. **Start the frontend** (from the frontend directory):
```bash
cd ../frontend
npm run dev
```

3. Open your browser and navigate to:
```
http://localhost:5173
```

## Project Structure

```
frontend/
├── public/              # Static assets
├── src/
│   ├── components/      # React components
│   │   ├── Sidebar.jsx         # Left navigation sidebar
│   │   ├── Dashboard.jsx       # Main dashboard container
│   │   ├── ComplaintTable.jsx  # Complaint list table
│   │   └── StatusDropdown.jsx  # Status editor
│   ├── services/
│   │   └── api.js              # API service layer
│   ├── App.jsx          # Main app component
│   ├── main.jsx         # React entry point
│   └── index.css        # Global styles
├── index.html           # HTML entry point
├── package.json         # Dependencies
└── vite.config.js       # Vite configuration
```

## Key Components

### Dashboard
- Fetches complaints and call logs on mount
- Auto-refreshes data every 5 seconds
- Manages complaint state and updates

### ComplaintTable
- Displays complaints in a scrollable table
- Maps phone numbers from CallLog data
- Applies priority-based styling to rows

### StatusDropdown
- Allows managers to update complaint status
- Shows loading state during updates
- Displays checkmark for resolved/closed items

### API Service
- `fetchComplaints()` - GET all complaints
- `updateComplaintStatus(id, status)` - PATCH complaint status
- `fetchCallLogs()` - GET call logs for phone numbers

## Configuration

The backend API URL is configured in `src/services/api.js`:
```javascript
const BASE_URL = 'http://localhost:8000';
```

Change this if your backend runs on a different host/port.

## Build for Production

```bash
npm run build
```

This creates an optimized production build in the `dist/` directory.

## Troubleshooting

**CORS errors:**
- Ensure the backend has CORS middleware enabled
- Check that the frontend URL is in the allowed origins list

**Complaints not loading:**
- Verify the backend is running on port 8000
- Check browser console for API errors
- Ensure the database has some complaint data

**Status updates not working:**
- Check network tab for failed PATCH requests
- Verify the complaint ID exists in the database
