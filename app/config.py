import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Strava API
    strava_client_id: str = ""
    strava_client_secret: str = ""
    
    # Base de datos
    database_url: str = "sqlite:///./strava_data.db"
    
    # Servidor
    app_url: str = "http://localhost:8000"
    secret_key: str = "your-secret-key-change-this"
    
    class Config:
        env_file = ".env"

settings = Settings()