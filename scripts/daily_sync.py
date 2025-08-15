#!/usr/bin/env python3
"""
Script de sincronización diaria para Strava API
Ejecutar con cron o GitHub Actions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json
import time
import logging
from typing import Dict

# Importar desde la app
from app.database import SessionLocal, Athlete, Activity
from app.strava_client import StravaClient
from app.config import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StravaETL:
    def __init__(self):
        self.strava_client = StravaClient(
            client_id=settings.strava_client_id,
            client_secret=settings.strava_client_secret
        )
        self.db = SessionLocal()
    
    def refresh_athlete_token(self, athlete: Athlete) -> bool:
        """Renueva el token de un atleta si es necesario"""
        current_time = int(time.time())
        
        # Si el token expira en menos de 1 hora, renovar
        if athlete.token_expires_at - current_time < 3600:
            logger.info(f"Renovando token para atleta {athlete.strava_id}")
            
            token_data = self.strava_client.refresh_token(athlete.refresh_token)
            if not token_data:
                logger.error(f"Error renovando token para atleta {athlete.strava_id}")
                return False
            
            athlete.access_token = token_data['access_token']
            athlete.refresh_token = token_data['refresh_token']
            athlete.token_expires_at = token_data['expires_at']
            self.db.commit()
            
            logger.info(f"Token renovado para atleta {athlete.strava_id}")
        
        return True
    
    def sync_athlete_activities(self, athlete: Athlete, days_back: int = 7) -> int:
        """Sincroniza actividades de un atleta"""
        if not self.refresh_athlete_token(athlete):
            return 0
        
        # Determinar fecha de inicio
        if athlete.last_sync:
            after_date = athlete.last_sync - timedelta(hours=1)  # 1h overlap
        else:
            after_date = datetime.now() - timedelta(days=days_back)
        
        logger.info(f"Sincronizando atleta {athlete.strava_id} desde {after_date}")
        
        # Obtener actividades
        activities = self.strava_client.get_activities(
            access_token=athlete.access_token,
            after=after_date
        )
        
        if not activities:
            logger.info(f"No hay nuevas actividades para atleta {athlete.strava_id}")
            return 0
        
        # Procesar actividades
        new_count = 0
        for activity_data in activities:
            if self.save_activity(athlete, activity_data):
                new_count += 1
            time.sleep(0.2)  # Rate limiting
        
        # Actualizar última sincronización
        athlete.last_sync = datetime.now()
        self.db.commit()
        
        logger.info(f"Sincronizadas {new_count} actividades nuevas para atleta {athlete.strava_id}")
        return new_count
    
    def save_activity(self, athlete: Athlete, activity_data: Dict) -> bool:
        """Guarda una actividad en la base de datos"""
        try:
            # Verificar si ya existe
            existing = self.db.query(Activity).filter(
                Activity.strava_id == activity_data['id']
            ).first()
            
            if existing:
                # Actualizar si no tiene datos detallados y ahora sí
                if not existing.has_detailed_data and self.should_get_detailed_data(activity_data):
                    detailed_data = self.strava_client.get_activity_detail(
                        athlete.access_token, 
                        activity_data['id']
                    )
                    if detailed_data:
                        self.update_activity_with_details(existing, detailed_data)
                        return True
                return False
            
            # Crear nueva actividad
            start_date = None
            if activity_data.get('start_date_local'):
                try:
                    start_date = datetime.fromisoformat(
                        activity_data['start_date_local'].replace('Z', '+00:00')
                    )
                except:
                    logger.warning(f"Error parsing date for activity {activity_data['id']}")
            
            activity = Activity(
                strava_id=activity_data['id'],
                athlete_id=athlete.strava_id,
                name=activity_data.get('name'),
                sport_type=activity_data.get('sport_type'),
                start_date=start_date,
                timezone=activity_data.get('timezone'),
                elapsed_time=activity_data.get('elapsed_time'),
                moving_time=activity_data.get('moving_time'),
                distance=activity_data.get('distance'),
                average_speed=activity_data.get('average_speed'),
                max_speed=activity_data.get('max_speed'),
                total_elevation_gain=activity_data.get('total_elevation_gain'),
                average_heartrate=activity_data.get('average_heartrate'),
                max_heartrate=activity_data.get('max_heartrate'),
                average_cadence=activity_data.get('average_cadence'),
                kudos_count=activity_data.get('kudos_count', 0),
                comment_count=activity_data.get('comment_count', 0),
                raw_data=json.dumps(activity_data, ensure_ascii=False)
            )
            
            # Obtener datos detallados si es necesario
            if self.should_get_detailed_data(activity_data):
                detailed_data = self.strava_client.get_activity_detail(
                    athlete.access_token, 
                    activity_data['id']
                )
                if detailed_data:
                    self.update_activity_with_details(activity, detailed_data)
                    time.sleep(0.5)  # Rate limiting para detalles
            
            self.db.add(activity)
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error guardando actividad {activity_data.get('id')}: {e}")
            self.db.rollback()
            return False
    
    def should_get_detailed_data(self, activity_data: Dict) -> bool:
        """Determina si se deben obtener datos detallados"""
        # Criterios para obtener detalles:
        # - Actividades de running o cycling
        # - Distancia > 1km
        # - Duración > 10 minutos
        sport_type = activity_data.get('sport_type', '').lower()
        distance = activity_data.get('distance', 0)
        elapsed_time = activity_data.get('elapsed_time', 0)
        
        return (
            sport_type in ['run', 'ride', 'virtualrun', 'virtualride'] and
            distance > 1000 and  # > 1km
            elapsed_time > 600   # > 10 min
        )
    
    def update_activity_with_details(self, activity: Activity, detailed_data: Dict):
        """Actualiza actividad con datos detallados"""
        # Marcar como con datos detallados
        activity.has_detailed_data = True
        
        # Actualizar raw_data con detalles completos
        activity.raw_data = json.dumps(detailed_data, ensure_ascii=False)
    
    def run_sync(self, days_back: int = 7):
        """Ejecuta sincronización completa"""
        logger.info("🔄 Iniciando sincronización diaria")
        
        # Obtener atletas activos
        athletes = self.db.query(Athlete).filter(Athlete.is_active == True).all()
        logger.info(f"Sincronizando {len(athletes)} atletas")
        
        total_new = 0
        errors = 0
        
        for athlete in athletes:
            try:
                new_activities = self.sync_athlete_activities(athlete, days_back)
                total_new += new_activities
                
                # Pausa entre atletas para respetar rate limits
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error sincronizando atleta {athlete.strava_id}: {e}")
                errors += 1
        
        logger.info(f"✅ Sincronización completada: {total_new} actividades nuevas, {errors} errores")
        
        # Estadísticas finales
        self.log_stats()
    
    def log_stats(self):
        """Registra estadísticas actuales"""
        total_athletes = self.db.query(Athlete).filter(Athlete.is_active == True).count()
        total_activities = self.db.query(Activity).count()
        recent_activities = self.db.query(Activity).filter(
            Activity.start_date >= datetime.now() - timedelta(days=7)
        ).count()
        
        logger.info(f"📊 Estadísticas: {total_athletes} atletas, {total_activities} actividades totales, {recent_activities} esta semana")
    
    def cleanup(self):
        """Limpieza final"""
        self.db.close()

def main():
    """Función principal del script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sincronización de datos Strava')
    parser.add_argument('--days', type=int, default=7, help='Días hacia atrás para sincronizar')
    parser.add_argument('--athlete-id', type=int, help='Sincronizar solo un atleta específico')
    
    args = parser.parse_args()
    
    etl = StravaETL()
    
    try:
        if args.athlete_id:
            # Sincronizar solo un atleta
            athlete = etl.db.query(Athlete).filter(
                Athlete.strava_id == args.athlete_id,
                Athlete.is_active == True
            ).first()
            
            if athlete:
                logger.info(f"Sincronizando solo atleta {args.athlete_id}")
                etl.sync_athlete_activities(athlete, args.days)
            else:
                logger.error(f"Atleta {args.athlete_id} no encontrado o inactivo")
        else:
            # Sincronización completa
            etl.run_sync(args.days)
            
    except KeyboardInterrupt:
        logger.info("Sincronización interrumpida por el usuario")
    except Exception as e:
        logger.error(f"Error en sincronización: {e}")
        sys.exit(1)
    finally:
        etl.cleanup()

if __name__ == "__main__":
    main()