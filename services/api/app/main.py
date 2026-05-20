from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

app = FastAPI(
    title="EventSales AI",
    description="AI-powered commercial intelligence for hospitality event sales.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "service": "eventsales-api"}


# Module routers are registered here as each module is implemented.
# Example (uncomment when the module is ready):
# from app.modules.restaurants.router import router as restaurants_router
# app.include_router(restaurants_router, prefix="/api/restaurants", tags=["restaurants"])
