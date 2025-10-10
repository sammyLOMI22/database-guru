"""FastAPI application factory"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import Settings

def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        docs_url="/docs" if settings.DEBUG else None,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": settings.VERSION}
    
    # TODO: Add more routers here
    # app.include_router(query.router, prefix="/api/query")
    
    return app