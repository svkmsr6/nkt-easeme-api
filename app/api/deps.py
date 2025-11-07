from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.security import get_current_user

async def Authed(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    return {"db": db, "user_id": user["user_id"]}
