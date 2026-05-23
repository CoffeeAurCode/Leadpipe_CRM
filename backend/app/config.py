from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    #Application configuration settings loaded from environment variables.
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    SUPABASE_JWT_SECRET: str = os.getenv("SUPABASE_JWT_SECRET", "")

    # Legacy DATABASE_URL (kept for backward compatibility if needed)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    OPEN_AI_API: str = os.getenv("OPEN_AI_API", "")
    # Vapi
    PRIVATE_VAPI_API: str = os.getenv("PRIVATE_VAPI_API", "")
    # Legacy single-assistant vars (kept for outbound call endpoint)
    VAPI_NUMBER_ID: str = os.getenv("VAPI_NUMBER_ID", "")
    VAPI_ASSISTANT_ID: str = os.getenv("VAPI_ASSISTANT_ID", "")
    # Complaint agent (global, Option B architecture)
    VAPI_COMPLAINT_ASSISTANT_ID: str = os.getenv("VAPI_COMPLAINT_ASSISTANT_ID", "")
    VAPI_COMPLAINT_NUMBER_ID: str = os.getenv("VAPI_COMPLAINT_NUMBER_ID", "")
    # Shared lease agent (existing property groups)
    VAPI_SHARED_LEASE_ASSISTANT_ID: str = os.getenv("VAPI_SHARED_LEASE_ASSISTANT_ID", "")
    VAPI_SHARED_LEASE_NUMBER_ID: str = os.getenv("VAPI_SHARED_LEASE_NUMBER_ID", "")
    VAPI_SHARED_LEASE_PHONE_NUMBER: str = os.getenv("VAPI_SHARED_LEASE_PHONE_NUMBER", "")
    # E.164 inbound number for the complaint agent (displayed in Voice Stats tab)
    VAPI_COMPLAINT_PHONE_NUMBER: str = os.getenv("VAPI_COMPLAINT_PHONE_NUMBER", "")
    BACKEND_URL: str = os.getenv("BACKEND_URL", "https://tenant-management-mvp.onrender.com")
    APP_NAME: str = os.getenv("APP_NAME", "Tenant Management System")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Twilio
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER: str = os.getenv("TWILIO_FROM_NUMBER", os.getenv("TWILIO_PHONE_NUMBER", ""))

    # Stripe
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_ID: str = os.getenv("STRIPE_PRICE_ID", "")

    # URLs
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    LANDING_PAGE_URL: str = os.getenv("LANDING_PAGE_URL", "http://localhost:3000")


settings = Settings()
