from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import artifacts_routes, auth_routes, discovery_routes, inspection_routes, verify_routes
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="MigrationProof API", version="0.1.0")

# CORS: locked to localhost in dev. In production, set FRONTEND_ORIGIN to the
# deployed Cloud Run frontend URL and add it here (see README Section 12) --
# never use a wildcard together with allow_credentials.
allowed_origins = ["http://localhost:5173", "http://127.0.0.1:5173"]
if settings.frontend_origin:
    allowed_origins.append(settings.frontend_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(artifacts_routes.router)
app.include_router(discovery_routes.router)
app.include_router(inspection_routes.router)
app.include_router(verify_routes.router)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok", "environment": settings.environment}
