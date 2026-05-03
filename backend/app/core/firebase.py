import firebase_admin
from app.config import settings

def init_firebase():
    if not firebase_admin._apps:
        if settings.FIREBASE_PROJECT_ID == "test":
            return
        # We only need the project ID to verify ID tokens, no service account needed!
        try:
            pass
        except Exception:
            pass
        firebase_admin.initialize_app(options={
            'projectId': settings.FIREBASE_PROJECT_ID
        })
