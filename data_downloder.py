#!/usr/bin/env python3
"""
Script simple para descargar datos de Strava desde Railway
Solo descarga - sin análisis
"""

import pandas as pd
import requests
import sqlite3
import zipfile
import os
from datetime import datetime

class StravaDataDownloader:
    def __init__(self, base_url="https://web-production-bc31.up.railway.app"):
        self.base_url = base_url
        self.data_dir = "strava_data"
        
        # Crear directorio si no existe
        os.makedirs(self.data_dir, exist_ok=True)
    
    def download_activities_csv(self):
        """Descarga actividades como CSV"""
        print("📊 Descargando actividades CSV...")
        
        try:
            response = requests.get(f"{self.base_url}/export/csv/activities", timeout=60)
            response.raise_for_status()
            
            # Guardar CSV con timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.data_dir}/strava_activities_{timestamp}.csv"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            # Info básica
            df = pd.read_csv(filename)
            file_size = os.path.getsize(filename) / 1024  # KB
            
            print(f"✅ Descarga completada:")
            print(f"   📄 Archivo: {filename}")
            print(f"   📊 Registros: {len(df)}")
            print(f"   💾 Tamaño: {file_size:.1f} KB")
            
            return filename
            
        except Exception as e:
            print(f"❌ Error descargando actividades: {e}")
            return None
    
    def download_athletes_csv(self):
        """Descarga atletas como CSV"""
        print("👥 Descargando atletas CSV...")
        
        try:
            response = requests.get(f"{self.base_url}/export/csv/athletes", timeout=30)
            response.raise_for_status()
            
            # Guardar CSV con timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.data_dir}/strava_athletes_{timestamp}.csv"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            # Info básica
            df = pd.read_csv(filename)
            file_size = os.path.getsize(filename) / 1024  # KB
            
            print(f"✅ Descarga completada:")
            print(f"   📄 Archivo: {filename}")
            print(f"   👥 Registros: {len(df)}")
            print(f"   💾 Tamaño: {file_size:.1f} KB")
            
            return filename
            
        except Exception as e:
            print(f"❌ Error descargando atletas: {e}")
            return None
    
    def download_backup_zip(self):
        """Descarga backup completo como ZIP"""
        print("📦 Descargando backup completo...")
        
        try:
            response = requests.get(f"{self.base_url}/export/backup", timeout=120)
            response.raise_for_status()
            
            # Guardar ZIP con timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{self.data_dir}/strava_backup_{timestamp}.zip"
            
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            file_size = os.path.getsize(filename) / 1024  # KB
            
            print(f"✅ Backup descargado:")
            print(f"   📦 Archivo: {filename}")
            print(f"   💾 Tamaño: {file_size:.1f} KB")
            
            # Extraer contenido
            extract_dir = f"{self.data_dir}/extracted_{timestamp}"
            with zipfile.ZipFile(filename, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
                files = zip_ref.namelist()
            
            print(f"   📂 Extraído en: {extract_dir}")
            print(f"   📋 Archivos: {', '.join(files)}")
            
            return filename, extract_dir
            
        except Exception as e:
            print(f"❌ Error descargando backup: {e}")
            return None, None
    
    def create_sqlite_database(self):
        """Crea base de datos SQLite local con los CSVs más recientes"""
        print("🗄️ Creando base de datos SQLite local...")
        
        try:
            # Buscar CSVs más recientes
            activities_files = [f for f in os.listdir(self.data_dir) if f.startswith('strava_activities_') and f.endswith('.csv')]
            athletes_files = [f for f in os.listdir(self.data_dir) if f.startswith('strava_athletes_') and f.endswith('.csv')]
            
            if not activities_files or not athletes_files:
                print("❌ No hay archivos CSV para procesar. Descarga primero.")
                return None
            
            # Usar los más recientes
            latest_activities = os.path.join(self.data_dir, max(activities_files))
            latest_athletes = os.path.join(self.data_dir, max(athletes_files))
            
            # Cargar en DataFrames
            activities_df = pd.read_csv(latest_activities)
            athletes_df = pd.read_csv(latest_athletes)
            
            # Crear base de datos SQLite
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            db_filename = f"{self.data_dir}/strava_local_{timestamp}.db"
            conn = sqlite3.connect(db_filename)
            
            # Guardar DataFrames
            activities_df.to_sql('activities', conn, if_exists='replace', index=False)
            athletes_df.to_sql('athletes', conn, if_exists='replace', index=False)
            
            # Crear índices básicos
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_athlete ON activities(athlete_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_date ON activities(start_date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_sport ON activities(sport_type)")
            
            conn.close()
            
            print(f"✅ Base de datos creada:")
            print(f"   🗄️ Archivo: {db_filename}")
            print(f"   📊 Actividades: {len(activities_df)} registros")
            print(f"   👥 Atletas: {len(athletes_df)} registros")
            print(f"   🔧 Para DBeaver: conecta a este archivo")
            
            return db_filename
            
        except Exception as e:
            print(f"❌ Error creando base de datos: {e}")
            return None
    
    def show_files(self):
        """Muestra archivos descargados"""
        print(f"\n📁 ARCHIVOS EN {self.data_dir}:")
        print("=" * 50)
        
        if not os.path.exists(self.data_dir):
            print("❌ Directorio no existe")
            return
        
        files = []
        for filename in os.listdir(self.data_dir):
            filepath = os.path.join(self.data_dir, filename)
            if os.path.isfile(filepath):
                size = os.path.getsize(filepath) / 1024  # KB
                mod_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                files.append((filename, size, mod_time))
        
        if not files:
            print("📂 Directorio vacío")
            return
        
        # Ordenar por fecha
        files.sort(key=lambda x: x[2], reverse=True)
        
        for filename, size, mod_time in files:
            file_type = "📊" if "activities" in filename else "👥" if "athletes" in filename else "📦" if filename.endswith('.zip') else "🗄️" if filename.endswith('.db') else "📄"
            print(f"   {file_type} {filename}")
            print(f"      💾 {size:.1f} KB - {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def check_server_status(self):
        """Verifica estado del servidor"""
        print("🔍 Verificando estado del servidor...")
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            print(f"✅ Servidor funcionando:")
            print(f"   📊 Estado: {data.get('status', 'unknown')}")
            print(f"   👥 Atletas: {data.get('athletes', 0)}")
            print(f"   🏃 Actividades: {data.get('activities', 0)}")
            print(f"   ⏰ Timestamp: {data.get('timestamp', 'unknown')}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error conectando al servidor: {e}")
            return False

def main():
    """Función principal"""
    downloader = StravaDataDownloader()
    
    print("📥 DESCARGADOR DE DATOS STRAVA")
    print("=" * 40)
    print("1. Descargar actividades (CSV)")
    print("2. Descargar atletas (CSV)")  
    print("3. Descargar backup completo (ZIP)")
    print("4. Descargar todo")
    print("5. Crear base de datos SQLite")
    print("6. Ver archivos descargados")
    print("7. Estado del servidor")
    
    choice = input("\nElige opción (1-7): ").strip()
    
    if choice == "1":
        filename = downloader.download_activities_csv()
        if filename:
            print(f"\n🎉 Listo para análisis:")
            print(f"   df = pd.read_csv('{filename}')")
    
    elif choice == "2":
        filename = downloader.download_athletes_csv()
        if filename:
            print(f"\n🎉 Listo para análisis:")
            print(f"   df = pd.read_csv('{filename}')")
    
    elif choice == "3":
        zip_file, extract_dir = downloader.download_backup_zip()
        if zip_file:
            print(f"\n🎉 Backup completo descargado")
    
    elif choice == "4":
        print("📥 Descargando todo...")
        
        activities_file = downloader.download_activities_csv()
        athletes_file = downloader.download_athletes_csv()
        backup_zip, backup_dir = downloader.download_backup_zip()
        
        success_count = sum([1 for f in [activities_file, athletes_file, backup_zip] if f])
        
        print(f"\n🎉 DESCARGA COMPLETA ({success_count}/3 exitosas):")
        if activities_file:
            print(f"   📊 Actividades: {os.path.basename(activities_file)}")
        if athletes_file:
            print(f"   👥 Atletas: {os.path.basename(athletes_file)}")
        if backup_zip:
            print(f"   📦 Backup: {os.path.basename(backup_zip)}")
        
        if activities_file and athletes_file:
            create_db = input("\n¿Crear base de datos SQLite? (y/n): ").lower() == 'y'
            if create_db:
                downloader.create_sqlite_database()
    
    elif choice == "5":
        db_file = downloader.create_sqlite_database()
        if db_file:
            print(f"\n🎉 Base de datos lista para DBeaver")
    
    elif choice == "6":
        downloader.show_files()
    
    elif choice == "7":
        downloader.check_server_status()
    
    else:
        print("❌ Opción inválida")

if __name__ == "__main__":
    main()