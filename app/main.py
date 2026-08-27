from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import create_db

# Routers
from app.api.user import router as user_router
from app.api.stock import router as stock_router
from app.api.article import router as article_router
from app.api.agent import router as agent_router
from app.api.telegram_webhook import router as telegram_router
from app.api.analysis import router as analysis_router  


app = FastAPI(
    title="MarketAI",
    description="AI-powered market analysis system",
    version="1.0.0"
)

# -----------------------------
# CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Routers
# -----------------------------
app.include_router(user_router)
app.include_router(stock_router)
app.include_router(article_router)
app.include_router(agent_router)
app.include_router(telegram_router)
app.include_router(analysis_router)   


# -----------------------------
# Startup event
# -----------------------------
@app.on_event("startup")
def on_startup():
    create_db()


# -----------------------------
# Health check
# -----------------------------
@app.get("/")
def root():
    return {"status": "ok", "message": "MarketAI backend is running"}
