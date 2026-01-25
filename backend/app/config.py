from dotenv import load_dotenv
import os

load_dotenv()


class Settings:
    #Application configuration settings loaded from environment variables.
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    APP_NAME: str = os.getenv("APP_NAME", "Tenant Management System")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ALLOWED_ORIGINS: list[str] = os.getenv("ALLOWED_ORIGINS", "").split(",")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))


settings = Settings()
