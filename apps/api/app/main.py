from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import animals, health

app = FastAPI(
    title="ZooLog AI API",
    description="Backend for ZooLog AI animal observation journals.",
    version="0.2.0",
)

# Allow the local Next.js dev server to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(animals.router)
