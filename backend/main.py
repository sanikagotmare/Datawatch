from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from core.database import init_db, SessionLocal
from routers import auth, datasets, pipelines, incidents, dashboard
from routers.datasources import router_ds, router_heal


def run_scheduled_monitoring():
    from models.pipeline import Pipeline
    from services.pipeline_service import run_monitoring_check
    db = SessionLocal()
    try:
        for pipeline in db.query(Pipeline).all():
            try:
                run_monitoring_check(db, pipeline)
            except Exception as e:
                print(f"[Scheduler] Pipeline {pipeline.id} failed: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_scheduled_monitoring, IntervalTrigger(hours=1), id="monitoring")
    scheduler.start()
    print("✅ DataWatch backend started. Scheduler running (hourly monitoring).")
    yield
    scheduler.shutdown()


app = FastAPI(
    title="DataWatch API",
    description="AI-powered self-healing data pipeline — Python + FastAPI + Gemini + ChromaDB",
    version="4.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",

        # Your Vercel frontend
        "https://datawatch-frontend-eta.vercel.app",
        "https://datawatch-frontend-ngin7244r-sanikagotmares-projects.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Existing routers
app.include_router(auth.router)
app.include_router(datasets.router)
app.include_router(pipelines.router)
app.include_router(incidents.router)
app.include_router(dashboard.router)

# New Feature 1+2+3 routers
app.include_router(router_ds)
app.include_router(router_heal)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "datawatch-api", "version": "4.0.0"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
