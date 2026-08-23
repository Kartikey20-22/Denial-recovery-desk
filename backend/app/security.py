from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.db import db
from app.models import User

ph=PasswordHash.recommended()
oauth=OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def hash_pw(p): return ph.hash(p)
def verify_pw(p,h): return ph.verify(p,h)
def token(uid):
    return jwt.encode({"sub":str(uid),"exp":datetime.now(timezone.utc)+timedelta(hours=12)},
                      settings.secret_key,algorithm="HS256")

async def current_user(t=Depends(oauth), s:AsyncSession=Depends(db)):
    try: uid=int(jwt.decode(t,settings.secret_key,algorithms=["HS256"])["sub"])
    except Exception: raise HTTPException(401,"Invalid token")
    u=await s.get(User,uid)
    if not u: raise HTTPException(401,"User not found")
    return u
