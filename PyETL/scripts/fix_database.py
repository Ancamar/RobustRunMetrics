#!/usr/bin/env python3
"""
Script para corregir la estructura de la base de datos
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sqlite3
from app.database import Base, engine, create_tables
from app.config import settings

def check_table_structure():
    """Verifica la estructura actual de las tablas"""
    db_path = settings.database_url.replace('sqlite:///', '')
    
    if not os.path.exists(db_path):
        print("❌ Base de datos no existe")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verificar tabla athletes
        cursor.execute("PRAGMA table_info(athletes)")
        athletes_columns = [row[1] for row in cursor.fetchall()]
        print(f"📊 Columnas en tabla 'athletes': {athletes_columns}")
        
        # Verificar tabla activities
        cursor.execute("PRAGMA table_info(activities)")
        activities_columns = [row[1] for row in cursor.fetchall()]
        print(f"📊 Columnas en tabla 'activities': {activities_columns}")
        
        # Verificar si faltan columnas importantes
        expected_activities_columns = ['strava_id', 'athlete_id', 'sport_type']
        missing = [col for col in expected_activities_columns if col not in activities_columns]
        
        if missing:
            print(f"❌ Faltan columnas en 'activities': {missing}")
            return False
        else:
            print("✅ Estructura de tablas correcta")
            return True
            
    except sqlite3.OperationalError as e:
        print(f"❌ Error verificando estructura: {e}")
        return False
    finally:
        conn.close()

def backup_data():
    """Hace backup de los datos existentes"""
    db_path = settings.database_url.replace('sqlite:///', '')
    
    if not os.path.exists(db_path):
        return
    
    backup_path = db_path + '.backup'
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"💾 Backup creado: {backup_path}")
    except Exception as e:
        print(f"⚠️ Error creando backup: {e}")

def recreate_database():
    """Recrea la base de datos con la estructura correcta"""
    db_path = settings.database_url.replace('sqlite:///', '')
    
    print("🔧 Recreando base de datos...")
    
    # Backup de datos existentes
    backup_data()
    
    # Eliminar base de datos actual
    if os.path.exists(db_path):
        os.remove(db_path)
        print("🗑️ Base de datos anterior eliminada")
    
    # Crear nueva estructura
    create_tables()
    print("✅ Nueva estructura creada")

def main():
    """Función principal - Modo automático"""
    print("🔍 Verificando estructura de base de datos...")
    
    if check_table_structure():
        print("\n✅ La base de datos está correcta. No se necesitan cambios.")
        return
    
    print("\n⚠️ La estructura de la base de datos necesita actualizarse.")
    print("🤖 Modo automático: Corrigiendo automáticamente...")
    
    recreate_database()
    
    # Verificar que todo está bien
    if check_table_structure():
        print("\n🎉 ¡Base de datos corregida exitosamente!")
        print("\n📋 Estado actual:")
        
        # Mostrar estado
        db_path = settings.database_url.replace('sqlite:///', '')
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM athletes")
        athletes_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM activities") 
        activities_count = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"   👥 Atletas: {athletes_count}")
        print(f"   🏃 Actividades: {activities_count}")
        
        print("\n🚀 Sistema listo para usar:")
        print("   1. uvicorn app.main:app --reload")
        print("   2. Ve a: http://localhost:8000")
        print("   3. Autoriza atletas para empezar a recopilar datos")
    else:
        print("\n❌ Hubo un problema recreando la base de datos")
        sys.exit(1)

if __name__ == "__main__":
    main()