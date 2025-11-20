from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user

def Authed(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return {"db": db, "user_id": user["user_id"]}
