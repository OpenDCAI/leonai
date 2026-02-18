"""Leon Web Backend - FastAPI Application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.web.core.lifespan import lifespan
from backend.web.routers import debug, sandbox, settings, threads, webhooks, workspace
from backend.web.monitor import router as monitor_router

# Create FastAPI app
app = FastAPI(title="Leon Web Backend", lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(threads.router)
app.include_router(sandbox.router)
app.include_router(webhooks.router)
app.include_router(workspace.router)
app.include_router(settings.router)
app.include_router(debug.router)
app.include_router(monitor_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
