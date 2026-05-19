"""
Japan Real Estate AI - FastAPI Main Entry
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)

from app.routers import line, property

app = FastAPI(
    title="Japan Real Estate AI",
    description="LINE Bot for Japanese Real Estate Consulting",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(line.router, prefix="/line", tags=["LINE"])
app.include_router(property.router, prefix="/api/property", tags=["Property"])


@app.get("/")
def root():
    return {"message": "Japan Real Estate AI API", "version": "1.0.0"}