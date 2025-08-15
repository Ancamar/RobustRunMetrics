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
        case_sensitive = False

# Debug: Imprimir variables de entorno directamente
print("🔍 DEBUG - Variables de entorno directas:")
print(f"   APP_URL (directo): {os.getenv('APP_URL', 'NO ENCONTRADA')}")
print(f"   STRAVA_CLIENT_ID (directo): {os.getenv('STRAVA_CLIENT_ID', 'NO ENCONTRADA')}")
print(f"   DATABASE_URL (directo): {os.getenv('DATABASE_URL', 'NO ENCONTRADA')}")

settings = Settings()

# Debug: Imprimir lo que cargó pydantic
print("🔍 DEBUG - Variables cargadas por pydantic:")
print(f"   app_url: {settings.app_url}")
print(f"   strava_client_id: {settings.strava_client_id}")
print(f"   database_url: {settings.database_url}")