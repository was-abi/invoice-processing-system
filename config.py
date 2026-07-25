# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file (using Context7 best practices)
load_dotenv()

class Settings:
    """Application settings from environment variables"""
    
    # Database
    DATABASE_HOST: str = os.getenv("DATABASE_HOST", "localhost")
    DATABASE_PORT: int = int(os.getenv("DATABASE_PORT", "5432"))
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "invoice_db")
    DATABASE_USER: str = os.getenv("DATABASE_USER", "postgres")
    DATABASE_PASSWORD: str = os.getenv("DATABASE_PASSWORD", "password123")
    
    # Ollama
    OLLAMA_HOST: str = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    
    # FastAPI
    API_TITLE: str = os.getenv("API_TITLE", "Invoice Processing System")
    API_VERSION: str = os.getenv("API_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    @property
    def database_url(self) -> dict:
        """Return database configuration as dict"""
        return {
            "host": self.DATABASE_HOST,
            "database": self.DATABASE_NAME,
            "user": self.DATABASE_USER,
            "password": self.DATABASE_PASSWORD,
            "port": self.DATABASE_PORT
        }
    LOKI_URL = os.getenv("LOKI_URL", "http://localhost:3100")
    LOKI_ENABLED = os.getenv("LOKI_ENABLED", "False").lower() == "true"

# Create global settings instance
settings = Settings()