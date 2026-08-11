"""
Vercel serverless function handler
Adapts FastAPI application to work with Vercel's serverless functions
"""

from mangum import Mangum
from src.api.main import app

# Create a Mangum handler to adapt FastAPI to ASGI/EWSGI for Vercel
handler = Mangum(app, lifespan="off")

# For Vercel, we need to export the handler
# Vercel looks for a handler function in the api directory
# This file would be placed in api/index.ts or similar in a JS/TS project
# For Python, we'll create a handler that Vercel can use

# This is a simplified version - in practice, Vercel Python support
# uses a different approach, but this shows the concept