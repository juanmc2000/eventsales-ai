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


from app.modules.restaurants.router import router as restaurants_router
from app.modules.personas.router import restaurant_assignment_router, router as personas_router
from app.modules.pricing.router import router as pricing_router

app.include_router(restaurants_router)
app.include_router(personas_router)
app.include_router(restaurant_assignment_router)
app.include_router(pricing_router)
