from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import complaints, voice, call_logs, flats, appointments, tenants
from app.config import settings

app = FastAPI(title="AI Complaint System")

# Get allowed origins from environment variable, fallback to localhost for development
allowed_origins = settings.ALLOWED_ORIGINS.split(",") if settings.ALLOWED_ORIGINS else [
    "http://localhost:5173", 
    "http://localhost:3000",
    "https://starlit-baklava-5b31c0.netlify.app"  # Netlify production URL
]

print(f"🔧 CORS Allowed Origins: {allowed_origins}")  # Debug log

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(complaints.router)
app.include_router(voice.router)
app.include_router(call_logs.router)
app.include_router(flats.router)
app.include_router(appointments.router)
app.include_router(tenants.router)  # NEW: Tenant management routes


@app.get("/")
async def root():
    return {"status": "Backend running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
