import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class StravaClient:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://www.strava.com/api/v3"
        self.auth_url = "https://www.strava.com/oauth"
        
    def get_authorization_url(self, redirect_uri: str, state: str = None) -> str:
        """Genera URL de autorización OAuth2"""
        scope = "read,activity:read_all,profile:read_all"
        url = (
            f"{self.auth_url}/authorize?"
            f"client_id={self.client_id}&"
            f"response_type=code&"
            f"redirect_uri={redirect_uri}&"
            f"approval_prompt=force&"
            f"scope={scope}"
        )
        if state:
            url += f"&state={state}"
        return url
    
    def exchange_token(self, authorization_code: str) -> Optional[Dict]:
        """Intercambia código por tokens"""
        try:
            response = requests.post(f"{self.auth_url}/token", data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': authorization_code,
                'grant_type': 'authorization_code'
            })
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error exchanging token: {e}")
            return None
    
    def refresh_token(self, refresh_token: str) -> Optional[Dict]:
        """Renueva access token"""
        try:
            response = requests.post(f"{self.auth_url}/token", data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': refresh_token,
                'grant_type': 'refresh_token'
            })
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return None
    
    def get_athlete(self, access_token: str) -> Optional[Dict]:
        """Obtiene información del atleta"""
        return self._api_call(access_token, "/athlete")
    
    def get_activities(self, access_token: str, after: datetime = None, per_page: int = 200) -> List[Dict]:
        """Obtiene actividades del atleta"""
        params = {'per_page': per_page}
        if after:
            params['after'] = int(after.timestamp())
        
        activities = []
        page = 1
        
        while True:
            params['page'] = page
            batch = self._api_call(access_token, "/athlete/activities", params=params)
            
            if not batch:
                break
                
            activities.extend(batch)
            if len(batch) < per_page:  # Última página
                break
                
            page += 1
            time.sleep(0.5)  # Rate limiting
            
        return activities
    
    def get_activity_detail(self, access_token: str, activity_id: int) -> Optional[Dict]:
        """Obtiene detalle completo de una actividad"""
        return self._api_call(access_token, f"/activities/{activity_id}")
    
    def _api_call(self, access_token: str, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Realiza llamada a la API con manejo de errores"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(f"{self.base_url}{endpoint}", headers=headers, params=params)
            
            if response.status_code == 401:
                logger.warning("Token expired or invalid")
                return None
            elif response.status_code == 429:
                # Rate limit exceeded
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limit exceeded, waiting {retry_after}s")
                time.sleep(retry_after)
                return self._api_call(access_token, endpoint, params)
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"API call failed for {endpoint}: {e}")
            return None