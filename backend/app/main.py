from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import init_db
from app.ai.checkpoint import graph_lifespan
from app.routes import auth,denials,reviews,dashboard,outcomes,workspace,copilot

@asynccontextmanager
async def life(app):
    await init_db()
    async with graph_lifespan():
        yield

app=FastAPI(title="Denial Recovery Desk",version="2.0.0",lifespan=life)
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origin_list,allow_credentials=True,
                   allow_methods=["*"],allow_headers=["*"])
app.include_router(auth.r,prefix="/api/auth",tags=["Auth"])
app.include_router(denials.r,prefix="/api/denials",tags=["Denials"])
app.include_router(reviews.r,prefix="/api/reviews",tags=["Human Review"])
app.include_router(dashboard.r,prefix="/api/dashboard",tags=["Dashboard"])
app.include_router(outcomes.r,prefix="/api/denials",tags=["Outcome & Payment"])
app.include_router(workspace.r,prefix="/api",tags=["Workspace"])
app.include_router(copilot.r,prefix="/api/copilot",tags=["AI RAG Copilot"])

@app.get("/health")
async def health():
    return {"status":"ok","llm_provider":settings.llm_provider,"llm_model":settings.llm_model or settings.ollama_model}
