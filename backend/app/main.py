from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import complaints, voice, call_logs, flats, appointments, tenants, properties, settings, rents, buildings, property_types, property_groups
from app.config import settings as config

app = FastAPI(title="AI Complaint System")

# CORS Configuration - HARDCODED FOR VAPI
# Bypassing environment variable to ensure it works
# This allows requests from Vapi, ngrok, and all external tools

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # HARDCODED - Allow ALL origins
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(complaints.router)
app.include_router(voice.router)
app.include_router(call_logs.router)
app.include_router(flats.router)
app.include_router(appointments.router)
app.include_router(tenants.router)  # NEW: Tenant management routes
app.include_router(properties.router)  # NEW: Properties listing routes
app.include_router(settings.router)  # NEW: Feature settings routes
app.include_router(rents.router)      # Rent management routes
app.include_router(buildings.router)  # NEW: Buildings hierarchy routes
app.include_router(property_types.router)  # NEW: Property type classifications
app.include_router(property_groups.router)  # NEW: Top-level property group entities


@app.get("/")
async def root():
    return {"status": "Backend running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
