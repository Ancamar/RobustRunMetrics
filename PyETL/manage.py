#!/usr/bin/env python3
"""
Script de gestión del sistema Strava - Comando único para todo
"""

import sys
import os
import subprocess
import argparse

# Agregar path de la app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_setup():
    """Ejecuta configuración automática"""
    print("🛠️ Ejecutando configuración automática...")
    subprocess.run([sys.executable, 'scripts/auto_setup.py'])

def run_server():
    """Ejecuta el servidor"""
    print("🚀 Iniciando servidor...")
    subprocess.run(['uvicorn', 'app.main:app', '--reload'])

def run_sync(days=7):
    """Ejecuta sincronización"""
    print(f"🔄 Sincronizando últimos {days} días...")
    subprocess.run([sys.executable, 'scripts/daily_sync.py', '--days', str(days)])

def run_analysis():
    """Ejecuta análisis de datos"""
    print("📊 Ejecutando análisis de datos...")
    subprocess.run([sys.executable, 'scripts/data_analysis.py'])

def show_status():
    """Muestra estado del sistema"""
    try:
        from app.database import SessionLocal, Athlete, Activity
        from app.config import settings
        
        db = SessionLocal()
        athletes = db.query(Athlete).count()
        activities = db.query(Activity).count()
        active_athletes = db.query(Athlete).filter(Athlete.is_active == True).count()
        db.close()
        
        print("\n📊 ESTADO DEL SISTEMA")
        print("=" * 30)
        print(f"👥 Atletas registrados: {athletes}")
        print(f"✅ Atletas activos: {active_athletes}")
        print(f"🏃 Actividades totales: {activities}")
        print(f"🗄️ Base de datos: {settings.database_url}")
        print(f"🌐 URL servidor: {settings.app_url}")
        
    except Exception as e:
        print(f"❌ Error obteniendo estado: {e}")

def fix_database():
    """Corrige problemas de base de datos"""
    print("🔧 Corrigiendo base de datos...")
    subprocess.run([sys.executable, 'scripts/fix_database.py'])

def main():
    parser = argparse.ArgumentParser(description='Gestión del sistema Strava')
    parser.add_argument('command', choices=[
        'setup', 'server', 'sync', 'analysis', 'status', 'fix-db'
    ], help='Comando a ejecutar')
    parser.add_argument('--days', type=int, default=7, help='Días para sincronizar')
    
    args = parser.parse_args()
    
    commands = {
        'setup': run_setup,
        'server': run_server,
        'sync': lambda: run_sync(args.days),
        'analysis': run_analysis,
        'status': show_status,
        'fix-db': fix_database
    }
    
    print(f"🎯 Ejecutando: {args.command}")
    commands[args.command]()

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("🛠️ GESTOR DEL SISTEMA STRAVA")
        print("=" * 30)
        print("\n📋 Comandos disponibles:")
        print("  python manage.py setup     - Configuración automática")
        print("  python manage.py server    - Iniciar servidor")
        print("  python manage.py sync      - Sincronizar datos")
        print("  python manage.py analysis  - Análisis de datos")
        print("  python manage.py status    - Estado del sistema")
        print("  python manage.py fix-db    - Corregir base de datos")
        print("\n📖 Ejemplos:")
        print("  python manage.py sync --days 30")
        print("  python manage.py setup && python manage.py server")
    else:
        main()