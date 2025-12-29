#!/usr/bin/env python3
"""
Script de configuración automática completa del sistema
"""

import sys
import os
import subprocess
import importlib.util

# Agregar path de la app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_dependencies():
    """Verifica que las dependencias estén instaladas"""
    required_packages = [
        'fastapi', 'uvicorn', 'sqlalchemy', 'pydantic_settings', 
        'requests', 'python-multipart'
    ]
    
    missing = []
    for package in required_packages:
        if importlib.util.find_spec(package) is None:
            missing.append(package)
    
    return missing

def install_dependencies():
    """Instala dependencias faltantes"""
    print("📦 Instalando dependencias...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Dependencias instaladas")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error instalando dependencias: {e}")
        return False

def check_config():
    """Verifica configuración de variables de entorno"""
    env_file = '.env'
    if not os.path.exists(env_file):
        print("❌ Archivo .env no encontrado")
        return False
    
    with open(env_file, 'r') as f:
        content = f.read()
    
    required_vars = ['STRAVA_CLIENT_ID', 'STRAVA_CLIENT_SECRET']
    missing = []
    
    for var in required_vars:
        if var not in content or f'{var}=tu_' in content:
            missing.append(var)
    
    if missing:
        print(f"⚠️ Variables de entorno faltantes o no configuradas: {missing}")
        print("📝 Edita el archivo .env con tus credenciales de Strava API")
        return False
    
    print("✅ Configuración de variables correcta")
    return True

def setup_database():
    """Configura la base de datos automáticamente"""
    print("🗄️ Configurando base de datos...")
    
    try:
        # Importar después de verificar dependencias
        from app.database import create_tables, SessionLocal, Athlete, Activity
        from app.config import settings
        
        # Crear tablas
        create_tables()
        
        # Verificar que funcionan las consultas básicas
        db = SessionLocal()
        athlete_count = db.query(Athlete).count()
        activity_count = db.query(Activity).count()
        db.close()
        
        print(f"✅ Base de datos configurada (Atletas: {athlete_count}, Actividades: {activity_count})")
        return True
        
    except Exception as e:
        print(f"❌ Error configurando base de datos: {e}")
        return False

def test_server():
    """Prueba que el servidor se puede importar correctamente"""
    print("🚀 Verificando servidor...")
    
    try:
        from app.main import app
        print("✅ Servidor se puede importar correctamente")
        return True
    except Exception as e:
        print(f"❌ Error con el servidor: {e}")
        return False

def show_next_steps():
    """Muestra los próximos pasos"""
    print("\n" + "="*60)
    print("🎉 ¡CONFIGURACIÓN COMPLETADA EXITOSAMENTE!")
    print("="*60)
    
    print("\n🚀 Para iniciar el sistema:")
    print("   uvicorn app.main:app --reload")
    
    print("\n🌐 URLs importantes:")
    print("   • Página principal: http://localhost:8000")
    print("   • Estadísticas: http://localhost:8000/stats")
    print("   • Estado del sistema: http://localhost:8000/health")
    
    print("\n👥 Para agregar atletas:")
    print("   1. Comparte: http://localhost:8000")
    print("   2. Los atletas autorizan su cuenta de Strava")
    print("   3. El sistema sincroniza automáticamente")
    
    print("\n🔄 Para sincronizar manualmente:")
    print("   python scripts/daily_sync.py")
    
    print("\n📊 Para análisis de datos:")
    print("   python scripts/data_analysis.py")
    
    print("\n📝 Configuración en Strava API:")
    print("   • Authorization Callback Domain: localhost")
    print("   • Website: http://localhost:8000")

def main():
    """Configuración automática completa"""
    print("🛠️ CONFIGURACIÓN AUTOMÁTICA DEL SISTEMA STRAVA")
    print("=" * 50)
    
    # 1. Verificar dependencias
    print("\n1️⃣ Verificando dependencias...")
    missing = check_dependencies()
    if missing:
        print(f"📦 Dependencias faltantes: {missing}")
        if not install_dependencies():
            print("❌ No se pudieron instalar las dependencias")
            sys.exit(1)
    else:
        print("✅ Todas las dependencias están instaladas")
    
    # 2. Verificar configuración
    print("\n2️⃣ Verificando configuración...")
    if not check_config():
        print("\n📋 Para continuar:")
        print("   1. Edita el archivo .env con tus credenciales")
        print("   2. Ejecuta este script de nuevo")
        sys.exit(1)
    
    # 3. Configurar base de datos
    print("\n3️⃣ Configurando base de datos...")
    if not setup_database():
        print("❌ Error configurando base de datos")
        sys.exit(1)
    
    # 4. Verificar servidor
    print("\n4️⃣ Verificando servidor...")
    if not test_server():
        print("❌ Error con configuración del servidor")
        sys.exit(1)
    
    # 5. Mostrar próximos pasos
    show_next_steps()

if __name__ == "__main__":
    main()