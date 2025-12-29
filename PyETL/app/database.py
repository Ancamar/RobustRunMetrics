from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from datetime import datetime
from .config import settings

Base = declarative_base()

class Athlete(Base):
    __tablename__ = "athletes"
    
    id = Column(Integer, primary_key=True)
    strava_id = Column(Integer, unique=True, index=True)
    firstname = Column(String(100))
    lastname = Column(String(100))
    email = Column(String(255))
    
    access_token = Column(String(500))
    refresh_token = Column(String(500))
    token_expires_at = Column(Integer)
    
    created_at = Column(DateTime, default=func.now())
    last_sync = Column(DateTime)
    is_active = Column(Boolean, default=True)

class Activity(Base):
    __tablename__ = "activities"
    
    id = Column(Integer, primary_key=True)
    strava_id = Column(Integer, unique=True, index=True)
    athlete_id = Column(Integer, index=True)
    
    # Básicos
    name = Column(String(500))
    sport_type = Column(String(100))
    start_date = Column(DateTime)
    timezone = Column(String(100))
    
    # Métricas tiempo
    elapsed_time = Column(Integer)  # segundos
    moving_time = Column(Integer)   # segundos
    
    # Métricas distancia/velocidad
    distance = Column(Float)        # metros
    average_speed = Column(Float)   # m/s
    max_speed = Column(Float)       # m/s
    
    # Elevación
    total_elevation_gain = Column(Float)  # metros
    
    # Esfuerzo
    average_heartrate = Column(Float)
    max_heartrate = Column(Float)
    average_cadence = Column(Float)
    
    # Social
    kudos_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    
    # Datos completos JSON
    raw_data = Column(Text)
    
    # Control
    has_detailed_data = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

# Database setup
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Crea todas las tablas"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Dependency para obtener sesión de DB"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()