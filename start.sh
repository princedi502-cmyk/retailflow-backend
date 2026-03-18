#!/bin/bash

# Production startup script for Railway deployment
echo "Starting RetailFlow Backend..."

# Set Python path
export PYTHONPATH=$PYTHONPATH:/app

# Check if we're in production environment
if [ "$RAILWAY_ENVIRONMENT" = "production" ] || [ "$ENVIRONMENT" = "production" ]; then
    echo "Production environment detected"
    echo "Connecting to MongoDB Atlas..."
    
    # Start with production settings
    uvicorn app.main:app \
        --host 0.0.0.0 \
        --port ${PORT:-8000} \
        --workers 1 \
        --access-log \
        --log-level info
else
    echo "Development environment detected"
    echo "Connecting to database (Atlas first, fallback to local)..."
    
    # Start with development settings
    uvicorn app.main:app \
        --host 0.0.0.0 \
        --port ${PORT:-8000} \
        --reload \
        --access-log \
        --log-level info
fi
