#!/usr/bin/env python3
"""
Script para análisis de datos recopilados
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from sqlalchemy import create_engine
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import json

from app.config import settings

class StravaAnalysis:
    def __init__(self):
        self.engine = create_engine(settings.database_url)
    
    def load_activities_data(self, days_back: int = 180) -> pd.DataFrame:
        """Carga actividades en un DataFrame"""
        query = f"""
        SELECT 
            a.*,
            at.firstname,
            at.lastname,
            EXTRACT(HOUR FROM a.start_date) as hour_of_day,
            EXTRACT(DOW FROM a.start_date) as day_of_week
        FROM activities a
        JOIN athletes at ON a.athlete_id = at.strava_id
        WHERE a.start_date >= NOW() - INTERVAL '{days_back} days'
        AND a.sport_type IN ('Run', 'Ride')
        ORDER BY a.start_date DESC
        """
        
        df = pd.read_sql(query, self.engine)
        
        # Conversiones y cálculos
        df['start_date'] = pd.to_datetime(df['start_date'])
        df['distance_km'] = df['distance'] / 1000
        df['pace_min_km'] = np.where(
            df['distance_km'] > 0,
            (df['moving_time'] / 60) / df['distance_km'],
            np.nan
        )
        df['speed_kmh'] = df['average_speed'] * 3.6
        
        return df
    
    def generate_summary_stats(self, df: pd.DataFrame) -> dict:
        """Genera estadísticas resumen"""
        stats = {
            'total_activities': len(df),
            'total_athletes': df['athlete_id'].nunique(),
            'total_distance_km': df['distance_km'].sum(),
            'total_time_hours': df['moving_time'].sum() / 3600,
            'avg_distance_km': df['distance_km'].mean(),
            'avg_pace_min_km': df[df['sport_type'] == 'Run']['pace_min_km'].mean(),
            'avg_speed_kmh': df[df['sport_type'] == 'Ride']['speed_kmh'].mean(),
        }
        
        return stats
    
    def export_for_ml(self, df: pd.DataFrame, filename: str = 'strava_ml_data.csv'):
        """Prepara datos para Machine Learning"""
        
        # Features para ML
        ml_features = [
            'athlete_id', 'sport_type', 'distance_km', 'moving_time',
            'elapsed_time', 'average_speed', 'max_speed', 'total_elevation_gain',
            'average_heartrate', 'max_heartrate', 'average_cadence',
            'hour_of_day', 'day_of_week', 'pace_min_km', 'speed_kmh'
        ]
        
        # Filtrar y limpiar
        ml_df = df[ml_features].copy()
        
        # Encoding categórico
        ml_df = pd.get_dummies(ml_df, columns=['sport_type'], prefix='sport')
        
        # Manejar valores faltantes
        ml_df = ml_df.fillna(ml_df.median(numeric_only=True))
        
        # Guardar
        ml_df.to_csv(filename, index=False)
        print(f"📁 Datos exportados para ML: {filename}")
        print(f"📊 Shape: {ml_df.shape}")
        
        return ml_df

def main():
    """Función principal de análisis"""
    analysis = StravaAnalysis()
    
    print("📊 Cargando datos...")
    df = analysis.load_activities_data(days_back=180)
    print(f"✅ Cargadas {len(df)} actividades de {df['athlete_id'].nunique()} atletas")
    
    print("\n📈 Estadísticas resumen:")
    stats = analysis.generate_summary_stats(df)
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    
    print("\n🤖 Exportando datos para ML...")
    ml_df = analysis.export_for_ml(df)
    
    print("\n✅ Análisis completado!")

if __name__ == "__main__":
    main()