from fastapi import FastAPI, Request, Depends, HTTPException, Query, BackgroundTasks, Header
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from io import StringIO, BytesIO
import json
import os
import subprocess
import sys
import logging
import csv
import zipfile
from datetime import datetime, timedelta

from .database import get_db, create_tables, Athlete, Activity
from .strava_client import StravaClient
from .config import settings

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar app
app = FastAPI(title="Strava Data Collector", version="1.0.0")

# Cliente Strava
strava_client = StravaClient(
    client_id=settings.strava_client_id,
    client_secret=settings.strava_client_secret
)

# Modelo para request de sync
class SyncRequest(BaseModel):
    days: int = 7
    action: str = "sync"

def get_app_url():
    """Obtiene la URL correcta de la aplicación"""
    # Primero intentar usar APP_URL directamente
    if settings.app_url:
        # Asegurar que tenga https://
        if settings.app_url.startswith('http'):
            return settings.app_url
        else:
            return f"https://{settings.app_url}"
    
    # Si estamos en Railway, construir URL automáticamente
    if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('PORT'):
        return "https://web-production-bc31.up.railway.app"
    
    # Fallback local
    return "http://localhost:8000"

@app.on_event("startup")
async def startup_event():
    """Inicialización de la aplicación"""
    create_tables()
    app_url = get_app_url()
    print(f"🚀 Servidor iniciado en: {app_url}")
    print(f"📋 Variables: CLIENT_ID={settings.strava_client_id[:8]}...")
    print(f"🌐 APP_URL configurada: {settings.app_url}")
    print(f"🔧 Railway ENV: {os.getenv('RAILWAY_ENVIRONMENT', 'No')}")

@app.get("/", response_class=HTMLResponse)
async def home():
    """Página principal para autorización"""
    base_url = get_app_url()
    redirect_uri = f"{base_url}/callback"
    
    auth_url = strava_client.get_authorization_url(redirect_uri)
    
    html_content = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Autorización Strava - Tesis Doctoral</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
            .btn {{ background: #FC4C02; color: white; padding: 15px 30px; text-decoration: none; 
                    border-radius: 5px; display: inline-block; margin: 20px 0; }}
            .info {{ background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
            .warning {{ background: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 5px; }}
            .debug {{ background: #f8f9fa; padding: 10px; border-radius: 3px; font-size: 0.8em; color: #666; }}
        </style>
    </head>
    <body>
        <h1>🏃‍♂️ Sistema de Recolección de Datos</h1>
        <p>Bienvenido al sistema de recolección de datos para la tesis doctoral sobre análisis deportivo.</p>
        
        <div class="info">
            <h3>📊 ¿Qué datos recopilaremos?</h3>
            <ul>
                <li>✅ Actividades de running y cycling</li>
                <li>✅ Métricas de rendimiento (ritmo, distancia, elevación)</li>
                <li>✅ Datos de frecuencia cardíaca (si disponibles)</li>
            </ul>
        </div>
        
        <div class="warning">
            <strong>🔒 Privacidad garantizada:</strong>
            <ul>
                <li>❌ No publicaremos nada en tu nombre</li>
                <li>❌ Solo acceso de lectura a tus datos</li>
                <li>✅ Datos anonimizados para análisis</li>
                <li>✅ Puedes revocar acceso en cualquier momento</li>
            </ul>
        </div>
        
        <div style="text-align: center;">
            <a href="{auth_url}" class="btn">🔗 Autorizar con Strava</a>
        </div>
        
        <p><strong>Proceso:</strong></p>
        <ol>
            <li>Haz clic en "Autorizar con Strava"</li>
            <li>Inicia sesión en Strava si es necesario</li>
            <li>Confirma los permisos</li>
            <li>Volverás aquí con confirmación de éxito</li>
        </ol>
        
        <div style="text-align: center; margin-top: 40px;">
            <a href="/stats" style="color: #FC4C02;">📈 Ver estadísticas del estudio</a>
            <br><br>
            <a href="/export/csv/activities" style="color: #007bff;">📄 Descargar datos CSV</a>
        </div>
        
        <div class="debug">
            🔧 Debug info: Base URL = {base_url} | Callback = {redirect_uri}
        </div>
    </body>
    </html>
    '''
    return html_content

@app.get("/callback")
async def oauth_callback(code: str = Query(None), error: str = Query(None), db: Session = Depends(get_db)):
    """Callback de OAuth2"""
    if error:
        return HTMLResponse(f"<h1>❌ Error de autorización: {error}</h1>")
    
    if not code:
        return HTMLResponse("<h1>❌ Código de autorización faltante</h1>")
    
    # Intercambiar código por tokens
    token_data = strava_client.exchange_token(code)
    if not token_data:
        return HTMLResponse("<h1>❌ Error al obtener tokens</h1>")
    
    # Obtener datos del atleta
    athlete_data = strava_client.get_athlete(token_data['access_token'])
    if not athlete_data:
        return HTMLResponse("<h1>❌ Error al obtener datos del atleta</h1>")
    
    # Guardar en base de datos
    athlete = db.query(Athlete).filter(Athlete.strava_id == athlete_data['id']).first()
    if not athlete:
        athlete = Athlete(
            strava_id=athlete_data['id'],
            firstname=athlete_data.get('firstname', ''),
            lastname=athlete_data.get('lastname', ''),
            email=athlete_data.get('email', '')
        )
        db.add(athlete)
    
    # Actualizar tokens
    athlete.access_token = token_data['access_token']
    athlete.refresh_token = token_data['refresh_token']
    athlete.token_expires_at = token_data['expires_at']
    athlete.is_active = True
    
    db.commit()
    
    return HTMLResponse(f'''
    <div style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px; text-align: center;">
        <h1 style="color: #28a745;">✅ ¡Autorización Exitosa!</h1>
        <p>Hola <strong>{athlete_data.get('firstname', 'Atleta')}</strong>,</p>
        <p>Tu cuenta ha sido vinculada correctamente al sistema de recolección de datos.</p>
        
        <div style="background: #d4edda; padding: 20px; border-radius: 5px; margin: 20px 0;">
            <h3>🔄 Próximos pasos automáticos:</h3>
            <ul style="text-align: left;">
                <li>✅ Sincronización diaria de nuevas actividades</li>
                <li>✅ Descarga de datos históricos (últimos 6 meses)</li>
                <li>✅ Análisis y procesamiento para la investigación</li>
            </ul>
        </div>
        
        <p>🔒 <em>Recuerda: puedes revocar el acceso en cualquier momento desde tu configuración de Strava.</em></p>
        
        <div style="margin-top: 30px;">
            <a href="/stats" style="background: #FC4C02; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                📊 Ver estadísticas del estudio
            </a>
        </div>
    </div>
    ''')

@app.get("/stats", response_class=HTMLResponse)
async def stats(db: Session = Depends(get_db)):
    """Estadísticas del estudio - Compatible con SQLite"""
    try:
        # Consultas básicas
        total_athletes = db.query(Athlete).filter(Athlete.is_active == True).count()
        total_activities = db.query(Activity).count()
        
        # Actividades recientes (última semana)
        one_week_ago = datetime.now() - timedelta(days=7)
        recent_activities = db.query(Activity).filter(
            Activity.start_date >= one_week_ago
        ).count()
        
        # Actividades por deporte (usando SQLite)
        sports_query = db.query(
            Activity.sport_type, 
            func.count(Activity.id).label('count')
        ).group_by(Activity.sport_type).order_by(func.count(Activity.id).desc()).limit(5)
        
        sports_stats = []
        for sport, count in sports_query:
            if sport:  # Filtrar valores None
                sports_stats.append((sport, count))
        
        # Atletas más activos (últimos 30 días) - usando SQLite
        thirty_days_ago = datetime.now() - timedelta(days=30)
        active_athletes_query = db.query(
            Athlete.firstname,
            Athlete.lastname,
            func.count(Activity.id).label('activity_count')
        ).join(
            Activity, Athlete.strava_id == Activity.athlete_id
        ).filter(
            Activity.start_date >= thirty_days_ago
        ).group_by(
            Athlete.strava_id, Athlete.firstname, Athlete.lastname
        ).order_by(
            func.count(Activity.id).desc()
        ).limit(10)
        
        most_active = []
        for firstname, lastname, count in active_athletes_query:
            name = f"{firstname or ''} {lastname or ''}".strip() or "Usuario anónimo"
            most_active.append((name, count))
        
    except Exception as e:
        return HTMLResponse(f'''
        <div style="font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px;">
            <h1 style="color: #dc3545;">❌ Error en estadísticas</h1>
            <div style="background: #f8d7da; padding: 15px; border-radius: 5px;">
                <p><strong>Error:</strong> {str(e)}</p>
                <p>Esto puede deberse a que aún no hay datos en la base de datos.</p>
            </div>
            <div style="text-align: center; margin-top: 20px;">
                <a href="/" style="background: #FC4C02; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                    ← Volver al inicio
                </a>
            </div>
        </div>
        ''')
    
    # Crear HTML de deportes
    sports_html = ""
    if sports_stats:
        sports_html = '''
        <h3>🏃 Deportes más populares:</h3>
        <ul>'''
        for sport, count in sports_stats:
            sports_html += f"<li><strong>{sport}</strong>: {count} actividades</li>"
        sports_html += "</ul>"
    else:
        sports_html = "<p><em>No hay actividades registradas aún.</em></p>"
    
    # Crear HTML de atletas activos
    athletes_html = ""
    if most_active:
        athletes_html = '''
        <h3>🏆 Atletas más activos (últimos 30 días):</h3>
        <ol>'''
        for name, count in most_active:
            athletes_html += f"<li><strong>{name}</strong>: {count} actividades</li>"
        athletes_html += "</ol>"
    else:
        athletes_html = "<p><em>No hay actividades en los últimos 30 días.</em></p>"
    
    return HTMLResponse(f'''
    <div style="font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px;">
        <h1>📊 Estadísticas del Estudio</h1>
        
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 30px 0;">
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center;">
                <h2 style="color: #FC4C02; margin: 0;">{total_athletes}</h2>
                <p>Atletas registrados</p>
            </div>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center;">
                <h2 style="color: #28a745; margin: 0;">{total_activities}</h2>
                <p>Actividades totales</p>
            </div>
            <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center;">
                <h2 style="color: #17a2b8; margin: 0;">{recent_activities}</h2>
                <p>Esta semana</p>
            </div>
        </div>
        
        {sports_html}
        
        {athletes_html}
        
        <div style="margin-top: 40px; text-align: center;">
            <a href="/" style="background: #6c757d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                ← Volver al inicio
            </a>
            <a href="/health" style="background: #17a2b8; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">
                🔧 Estado del sistema
            </a>
            <br><br>
            <a href="/export/csv/activities" style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                📄 Descargar CSV
            </a>
            <a href="/export/backup" style="background: #ffc107; color: black; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">
                📦 Backup completo
            </a>
        </div>
        
        <p style="text-align: center; color: #666; margin-top: 20px; font-size: 0.9em;">
            Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
    ''')

@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check para monitoreo"""
    try:
        athlete_count = db.query(Athlete).count()
        activity_count = db.query(Activity).count()
        
        app_url = get_app_url()
        
        return {
            "status": "ok", 
            "timestamp": datetime.now(),
            "athletes": athlete_count,
            "activities": activity_count,
            "database": "connected",
            "app_url": app_url,
            "environment": "railway" if os.getenv('RAILWAY_ENVIRONMENT') else "local",
            "app_url_config": settings.app_url
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now(),
            "error": str(e)
        }

# ==========================================
# ENDPOINTS WEBHOOK
# ==========================================

@app.post("/webhook/sync")
async def webhook_sync(
    sync_request: SyncRequest,
    background_tasks: BackgroundTasks,
    authorization: str = Header(None)
):
    """Webhook para trigger sincronización desde GitHub Actions"""
    
    # Verificar token de autorización
    if not authorization or not authorization.startswith('Bearer '):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    
    token = authorization.split(' ')[1]
    if token != settings.sync_webhook_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Ejecutar sincronización en background
    background_tasks.add_task(run_sync_background, sync_request.days)
    
    logger.info(f"🔄 Sync triggered via webhook for {sync_request.days} days")
    
    return {
        "status": "triggered",
        "message": f"Sync started for last {sync_request.days} days",
        "timestamp": datetime.now()
    }

@app.get("/api/sync/status")
async def sync_status(db: Session = Depends(get_db)):
    """Endpoint para verificar estado de sincronización"""
    try:
        # Obtener última sincronización
        latest_sync = db.query(Athlete.last_sync).filter(
            Athlete.is_active == True,
            Athlete.last_sync.isnot(None)
        ).order_by(Athlete.last_sync.desc()).first()
        
        # Contar actividades recientes
        recent_activities = db.query(Activity).filter(
            Activity.start_date >= datetime.now() - timedelta(hours=24)
        ).count()
        
        # Contar atletas activos
        active_athletes = db.query(Athlete).filter(Athlete.is_active == True).count()
        
        return {
            "status": "ok",
            "last_sync": latest_sync[0] if latest_sync else None,
            "activities_last_24h": recent_activities,
            "active_athletes": active_athletes,
            "timestamp": datetime.now()
        }
        
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now()
        }

async def run_sync_background(days: int):
    """Ejecuta sincronización en background"""
    try:
        logger.info(f"🔄 Starting background sync for {days} days")
        
        # Ejecutar el script de sincronización
        result = subprocess.run([
            sys.executable, 'scripts/daily_sync.py', '--days', str(days)
        ], capture_output=True, text=True, cwd='.')
        
        if result.returncode == 0:
            logger.info("✅ Background sync completed successfully")
            logger.info(f"Sync output: {result.stdout}")
        else:
            logger.error(f"❌ Background sync failed: {result.stderr}")
        
    except Exception as e:
        logger.error(f"❌ Background sync exception: {e}")

# ==========================================
# ENDPOINTS DE EXPORTACIÓN
# ==========================================

@app.get("/export/database")
async def export_database(db: Session = Depends(get_db)):
    """Exporta toda la base de datos como JSON"""
    try:
        # Exportar atletas
        athletes = db.query(Athlete).all()
        athletes_data = []
        for athlete in athletes:
            athletes_data.append({
                'id': athlete.id,
                'strava_id': athlete.strava_id,
                'firstname': athlete.firstname,
                'lastname': athlete.lastname,
                'email': athlete.email,
                'created_at': athlete.created_at.isoformat() if athlete.created_at else None,
                'last_sync': athlete.last_sync.isoformat() if athlete.last_sync else None,
                'is_active': athlete.is_active
            })
        
        # Exportar actividades
        activities = db.query(Activity).all()
        activities_data = []
        for activity in activities:
            activities_data.append({
                'id': activity.id,
                'strava_id': activity.strava_id,
                'athlete_id': activity.athlete_id,
                'name': activity.name,
                'sport_type': activity.sport_type,
                'start_date': activity.start_date.isoformat() if activity.start_date else None,
                'timezone': activity.timezone,
                'elapsed_time': activity.elapsed_time,
                'moving_time': activity.moving_time,
                'distance': activity.distance,
                'average_speed': activity.average_speed,
                'max_speed': activity.max_speed,
                'total_elevation_gain': activity.total_elevation_gain,
                'average_heartrate': activity.average_heartrate,
                'max_heartrate': activity.max_heartrate,
                'average_cadence': activity.average_cadence,
                'kudos_count': activity.kudos_count,
                'comment_count': activity.comment_count,
                'has_detailed_data': activity.has_detailed_data,
                'raw_data': activity.raw_data,
                'created_at': activity.created_at.isoformat() if activity.created_at else None,
                'updated_at': activity.updated_at.isoformat() if activity.updated_at else None
            })
        
        return {
            "export_date": datetime.now().isoformat(),
            "athletes": athletes_data,
            "activities": activities_data,
            "summary": {
                "total_athletes": len(athletes_data),
                "total_activities": len(activities_data)
            }
        }
        
    except Exception as e:
        logger.error(f"Error exporting database: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export/csv/activities")
async def export_activities_csv(db: Session = Depends(get_db)):
    """Exporta actividades como CSV para análisis"""
    try:
        # Query con JOIN para obtener datos completos
        query = db.query(
            Activity.strava_id,
            Activity.athlete_id,
            Activity.name,
            Activity.sport_type,
            Activity.start_date,
            Activity.timezone,
            Activity.elapsed_time,
            Activity.moving_time,
            Activity.distance,
            Activity.average_speed,
            Activity.max_speed,
            Activity.total_elevation_gain,
            Activity.average_heartrate,
            Activity.max_heartrate,
            Activity.average_cadence,
            Activity.kudos_count,
            Activity.comment_count,
            Activity.has_detailed_data,
            Activity.created_at,
            Athlete.firstname,
            Athlete.lastname
        ).join(Athlete, Activity.athlete_id == Athlete.strava_id).order_by(Activity.start_date.desc())
        
        activities = query.all()
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Headers optimizados para análisis
        writer.writerow([
            'strava_id', 'athlete_id', 'athlete_name', 'activity_name', 'sport_type',
            'start_date', 'start_time', 'timezone', 'year', 'month', 'day_of_week',
            'distance_km', 'distance_m', 'moving_time_min', 'moving_time_sec', 
            'elapsed_time_min', 'elapsed_time_sec', 'average_speed_kmh', 'average_speed_ms',
            'max_speed_kmh', 'max_speed_ms', 'pace_min_km', 'total_elevation_gain',
            'average_heartrate', 'max_heartrate', 'average_cadence', 
            'kudos_count', 'comment_count', 'has_detailed_data', 'created_at'
        ])
        
        # Procesar datos
        for row in activities:
            (strava_id, athlete_id, name, sport_type, start_date, timezone, elapsed_time, 
             moving_time, distance, avg_speed, max_speed, elevation, avg_hr, max_hr, 
             cadence, kudos, comments, detailed, created_at, firstname, lastname) = row
            
            # Calcular campos derivados
            athlete_name = f"{firstname or ''} {lastname or ''}".strip() or "Anónimo"
            
            # Fechas
            date_str = start_date.strftime('%Y-%m-%d') if start_date else None
            time_str = start_date.strftime('%H:%M:%S') if start_date else None
            year = start_date.year if start_date else None
            month = start_date.month if start_date else None
            day_of_week = start_date.strftime('%A') if start_date else None
            
            # Distancias
            distance_km = round(distance / 1000, 3) if distance else None
            
            # Tiempos
            moving_min = round(moving_time / 60, 2) if moving_time else None
            elapsed_min = round(elapsed_time / 60, 2) if elapsed_time else None
            
            # Velocidades
            avg_speed_kmh = round(avg_speed * 3.6, 2) if avg_speed else None
            max_speed_kmh = round(max_speed * 3.6, 2) if max_speed else None
            
            # Pace (min/km) - solo para running
            pace_min_km = None
            if sport_type and 'run' in sport_type.lower() and distance and moving_time and distance > 0:
                pace_sec_per_m = moving_time / distance
                pace_min_km = round((pace_sec_per_m * 1000) / 60, 2)
            
            writer.writerow([
                strava_id, athlete_id, athlete_name, name, sport_type,
                date_str, time_str, timezone, year, month, day_of_week,
                distance_km, distance, moving_min, moving_time,
                elapsed_min, elapsed_time, avg_speed_kmh, avg_speed,
                max_speed_kmh, max_speed, pace_min_km, elevation,
                avg_hr, max_hr, cadence, kudos, comments, detailed,
                created_at.isoformat() if created_at else None
            ])
        
        output.seek(0)
        
        # Nombre con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"strava_activities_{timestamp}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/export/csv/athletes")
async def export_athletes_csv(db: Session = Depends(get_db)):
    """Exporta atletas como CSV"""
    try:
        athletes = db.query(Athlete).filter(Athlete.is_active == True).all()
        
        output = StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'id', 'strava_id', 'firstname', 'lastname', 'full_name', 'email',
            'created_at', 'last_sync', 'days_since_last_sync', 'is_active'
        ])
        
        for athlete in athletes:
            full_name = f"{athlete.firstname or ''} {athlete.lastname or ''}".strip()
            
            # Calcular días desde última sincronización
            days_since_sync = None
            if athlete.last_sync:
                delta = datetime.now() - athlete.last_sync
                days_since_sync = delta.days
            
            writer.writerow([
                athlete.id, athlete.strava_id, athlete.firstname, athlete.lastname,
                full_name, athlete.email,
                athlete.created_at.isoformat() if athlete.created_at else None,
                athlete.last_sync.isoformat() if athlete.last_sync else None,
                days_since_sync, athlete.is_active
            ])
        
        output.seek(0)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"strava_athletes_{timestamp}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting athletes CSV: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/debug/get-token")
async def get_debug_token(db: Session = Depends(get_db)):
    """SOLO PARA DESARROLLO - Obtener token válido"""
    athlete = db.query(Athlete).filter(Athlete.is_active == True).first()
    if athlete and athlete.access_token:
        return {
            "access_token": athlete.access_token,
            "athlete_name": f"{athlete.firstname} {athlete.lastname}",
            "expires_at": athlete.token_expires_at
        }
    return {"error": "No token found"}

@app.get("/debug/refresh-token")
async def refresh_token_debug(db: Session = Depends(get_db)):
    """Refresca token automáticamente"""
    import time
    
    athlete = db.query(Athlete).filter(Athlete.is_active == True).first()
    if not athlete or not athlete.refresh_token:
        return {"error": "No refresh token found"}
    
    # Refrescar usando el cliente Strava
    token_data = strava_client.refresh_token(athlete.refresh_token)
    if not token_data:
        return {"error": "Failed to refresh token"}
    
    # Actualizar en BD
    athlete.access_token = token_data['access_token']
    athlete.refresh_token = token_data['refresh_token']  
    athlete.token_expires_at = token_data['expires_at']
    db.commit()
    
    return {
        "access_token": token_data['access_token'],
        "expires_in_hours": (token_data['expires_at'] - int(time.time())) / 3600
    }

@app.get("/export/backup")
async def export_backup_zip(db: Session = Depends(get_db)):
    """Exporta backup completo como ZIP con CSVs y JSON"""
    try:
        # Crear ZIP en memoria
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            
            # 1. CSV de actividades
            activities_csv = StringIO()
            activities_writer = csv.writer(activities_csv)
            
            # Headers para actividades
            activities_writer.writerow([
                'strava_id', 'athlete_id', 'athlete_name', 'activity_name', 'sport_type',
                'start_date', 'distance_km', 'moving_time_min', 'average_speed_kmh',
                'total_elevation_gain', 'average_heartrate', 'max_heartrate'
            ])
            
            # Datos de actividades
            activities_query = db.query(
                Activity.strava_id, Activity.athlete_id, Activity.name, Activity.sport_type,
                Activity.start_date, Activity.distance, Activity.moving_time, Activity.average_speed,
                Activity.total_elevation_gain, Activity.average_heartrate, Activity.max_heartrate,
                Athlete.firstname, Athlete.lastname
            ).join(Athlete, Activity.athlete_id == Athlete.strava_id).all()
            
            for row in activities_query:
                athlete_name = f"{row[11] or ''} {row[12] or ''}".strip()
                activities_writer.writerow([
                    row[0], row[1], athlete_name, row[2], row[3],
                    row[4].isoformat() if row[4] else None,
                    round(row[5] / 1000, 2) if row[5] else None,
                    round(row[6] / 60, 2) if row[6] else None,
                    round(row[7] * 3.6, 2) if row[7] else None,
                    row[8], row[9], row[10]
                ])
            
            activities_csv.seek(0)
            zip_file.writestr('activities.csv', activities_csv.getvalue())
            
            # 2. CSV de atletas
            athletes_csv = StringIO()
            athletes_writer = csv.writer(athletes_csv)
            athletes_writer.writerow(['strava_id', 'firstname', 'lastname', 'email', 'last_sync', 'is_active'])
            
            athletes = db.query(Athlete).all()
            for athlete in athletes:
                athletes_writer.writerow([
                    athlete.strava_id, athlete.firstname, athlete.lastname, athlete.email,
                    athlete.last_sync.isoformat() if athlete.last_sync else None,
                    athlete.is_active
                ])
            
            athletes_csv.seek(0)
            zip_file.writestr('athletes.csv', athletes_csv.getvalue())
            
            # 3. JSON completo (como backup)
            backup_data = {
                "backup_date": datetime.now().isoformat(),
                "athletes_count": db.query(Athlete).count(),
                "activities_count": db.query(Activity).count(),
                "note": "Backup completo de la base de datos Strava"
            }
            
            zip_file.writestr('backup_info.json', json.dumps(backup_data, indent=2))
        
        zip_buffer.seek(0)
        
        # Nombre con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"strava_backup_{timestamp}.zip"
        
        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error creating backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)