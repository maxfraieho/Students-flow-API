"""StudentFlow FastAPI application — main entry point."""
from __future__ import annotations
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routers import (
    accounts,
    audit,
    credentials,
    handoff,
    prompts,
    repositories,
    settings,
    students,
    sync,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.bootstrap import create_app_dirs, init_db, init_logging
    create_app_dirs()
    init_logging()
    init_db()
    yield


app = FastAPI(
    title="StudentFlow API",
    version="1.0.0",
    description="REST API gateway for the StudentFlow system.",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = round((time.perf_counter() - start) * 1000, 1)
    response.headers["X-Process-Time-Ms"] = str(elapsed)
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


API = "/api"

app.include_router(students.router, prefix=API)
app.include_router(accounts.router, prefix=API)
app.include_router(credentials.router, prefix=API)
app.include_router(repositories.router, prefix=API)
app.include_router(sync.router, prefix=API)
app.include_router(handoff.router, prefix=API)
app.include_router(prompts.router, prefix=API)
app.include_router(audit.router, prefix=API)
app.include_router(settings.router, prefix=API)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "studentflow-api"}


@app.get("/api/version")
def version():
    return {"version": "1.0.0", "name": "StudentFlow API"}
