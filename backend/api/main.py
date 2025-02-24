from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import batteries, sources, data, optimization

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint (keep it simple here)
@app.get("/health")
def health_check():
    return {"status": "ok"}


# Mount route modules
app.include_router(batteries.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
app.include_router(data.router, prefix="/api")
app.include_router(optimization.router, prefix="/api")
