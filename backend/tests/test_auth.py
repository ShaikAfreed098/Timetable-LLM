from unittest.mock import patch
from app.models.institution import Institution
from app.models.invite import Invite
from app.models.user import User

def test_login_google_rollback_on_db_failure(client, db):
    """If DB commit fails during user creation, Firebase user should be deleted."""
    inst = db.query(Institution).first()
    email = "rollback-test@example.com"
    uid = "rollback-uid-123"
    
    # Ensure no user exists with this email
    db.query(User).filter(User.email == email).delete()
    
    from datetime import datetime, timedelta
    import secrets
    invite = Invite(
        email=email, 
        institution_id=inst.id, 
        role="staff",
        token=secrets.token_urlsafe(32),
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(invite)
    db.commit()

    with patch("app.api.auth.firebase_auth.verify_id_token") as mock_verify:
        mock_verify.return_value = {"email": email, "uid": uid}
        
        with patch("app.api.auth.firebase_auth.delete_user") as mock_delete:
            # We need to patch the session commit that happens inside the router
            # Since 'db' is injected, we can patch its commit method
            with patch.object(db, "commit", side_effect=Exception("DB FAIL")):
                response = client.post("/api/auth/google", json={"token": "valid-token"})
                
                assert response.status_code == 500
                assert "Failed to create user account" in response.json()["detail"]
                
                # Verify delete_user was called for the new Firebase user
                mock_delete.assert_called_once_with(uid)
