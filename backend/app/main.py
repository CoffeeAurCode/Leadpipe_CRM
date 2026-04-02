from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import (
    complaints, voice, call_logs, flats, appointments, tenants,
    properties, settings, rents, buildings, property_types,
    property_groups, upload, workflow, chat, payments,
)
from app.config import settings as config

app = FastAPI(title="AI Complaint System")

# CORS — locked to configured origins.
# VAPI/Stripe call server-to-server, so CORS does not apply to them.
allowed_origins = [
    origin.strip()
    for origin in config.ALLOWED_ORIGINS.split(",")
    if origin.strip()
]
# Fallback for local dev if ALLOWED_ORIGINS is empty
if not allowed_origins:
    allowed_origins = ["http://localhost:3000", "http://localhost:5173"]

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
app.include_router(tenants.router)
app.include_router(properties.router)
app.include_router(settings.router)
app.include_router(rents.router)
app.include_router(buildings.router)
app.include_router(property_types.router)
app.include_router(property_groups.router)
app.include_router(upload.router)
app.include_router(workflow.router)
app.include_router(chat.router)
app.include_router(payments.router)


@app.get("/")
async def root():
    return {"status": "Backend running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
