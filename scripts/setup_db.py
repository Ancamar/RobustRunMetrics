#!/usr/bin/env python3
"""
Script de inicialización de base de datos
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import create_tables, SessionLocal, Athlete
from app.config import settings

def main():
    print("🔧 Inicializando base de datos...")
    
    # Crear tablas
    create_tables()
    print("✅ Tablas creadas")
    
    # Verificar conexión
    db = SessionLocal()
    try:
        count = db.query(Athlete).count()
        print(f"📊 Atletas registrados: {count}")
        print(f"🌐 URL del servidor: {settings.app_url}")
        print(f"🔗 URL de autorización: {settings.app_url}")
    finally:
        db.close()
    
    print("\n🚀 Sistema listo para usar!")
    print(f"   1. Ejecuta: uvicorn app.main:app --reload")
    print(f"   2. Ve a: {settings.app_url}")
    print(f"   3. Comparte la URL con los atletas")

if __name__ == "__main__":
    main()