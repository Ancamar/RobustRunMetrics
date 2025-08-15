from fastapi import FastAPI, Request, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import os
from datetime import datetime, timedelta

from .database import get_db, create_tables, Athlete, Activity
from .strava_client import StravaClient
from .config import settings

# Inicializar app
app = FastAPI(title="Strava Data Collector", version="1.0.0")

# Cliente Strava
strava_client = StravaClient(
    client_id=settings.strava_client_id,
    client_secret=settings.strava_client_secret
)

@app.on_event("startup")
async def startup_event():
    """Inicialización de la aplicación"""
    create_tables()
    # Detectar si estamos en Railway o local
    railway_url = os.getenv('RAILWAY_STATIC_URL')
    app_url = railway_url or settings.app_url
    print(f"🚀 Servidor iniciado en: {app_url}")
    print(f"📋 Variables: CLIENT_ID={settings.strava_client_id[:8]}...")

@app.get("/", response_class=HTMLResponse)
async def home():
    """Página principal para autorización"""
    # Usar URL de Railway si está disponible
    railway_url = os.getenv('RAILWAY_STATIC_URL')
    base_url = railway_url or settings.app_url
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
        
        railway_url = os.getenv('RAILWAY_STATIC_URL')
        app_url = railway_url or settings.app_url
        
        return {
            "status": "ok", 
            "timestamp": datetime.now(),
            "athletes": athlete_count,
            "activities": activity_count,
            "database": "connected",
            "app_url": app_url,
            "environment": "railway" if railway_url else "local"
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now(),
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)