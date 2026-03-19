"""Entry point for StudentFlow FastAPI backend."""
import os
import uvicorn
from app.bootstrap import create_app_dirs, init_db, init_logging

if __name__ == "__main__":
    create_app_dirs()
    init_logging()
    init_db()

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8050"))

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )
