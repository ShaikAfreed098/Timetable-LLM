import firebase_admin
from firebase_admin import credentials
from app.config import settings

def init_firebase():
    if not firebase_admin._apps:
        # We only need the project ID to verify ID tokens, no service account needed!
        firebase_admin.initialize_app(options={
            'projectId': settings.FIREBASE_PROJECT_ID
        })
