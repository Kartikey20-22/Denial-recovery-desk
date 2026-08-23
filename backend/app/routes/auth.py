from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import db
from app.models import User
from app.schemas import Login,Register
from app.security import hash_pw,verify_pw,token

r=APIRouter()

@r.post("/register")
async def register(x:Register,s:AsyncSession=Depends(db)):
    if await s.scalar(select(User).where(User.email==x.email.lower())): raise HTTPException(409,"Email exists")
    u=User(email=x.email.lower(),password_hash=hash_pw(x.password),name=x.name)
    s.add(u); await s.commit(); await s.refresh(u)
    return {"access_token":token(u.id),"token_type":"bearer"}

@r.post("/login")
async def login(x:Login,s:AsyncSession=Depends(db)):
    u=await s.scalar(select(User).where(User.email==x.email.lower()))
    if not u or not verify_pw(x.password,u.password_hash): raise HTTPException(401,"Invalid credentials")
    return {"access_token":token(u.id),"token_type":"bearer"}
