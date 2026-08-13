# Vercel serverless entrypoint for FastAPI
from src.api.main import app

# Vercel requires a top-level variable named "app"
# FastAPI will handle all routing normally
