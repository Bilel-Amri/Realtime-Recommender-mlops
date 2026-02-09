#!/bin/bash
# Docker deployment script for Real-Time Recommender System

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print header
echo -e "${BLUE}"
echo "============================================"
echo "Real-Time Recommender System - Docker Setup"
echo "============================================"
echo -e "${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    echo "Install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

echo -e "${GREEN}✅ Docker is installed${NC}"

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}❌ Docker Compose is not installed${NC}"
    echo "Install Docker Compose from: https://docs.docker.com/compose/install/"
    exit 1
fi

echo -e "${GREEN}✅ Docker Compose is installed${NC}"

# Check if dataset exists
if [ ! -d "data/processed" ] || [ ! -f "data/processed/interactions.csv" ]; then
    echo -e "${YELLOW}⚠️  Dataset not found${NC}"
    echo "Downloading and preprocessing dataset..."
    
    if command -v python3 &> /dev/null; then
        python3 data/download_dataset.py
    elif command -v python &> /dev/null; then
        python data/download_dataset.py
    else
        echo -e "${RED}❌ Python is not installed${NC}"
        echo "Install Python to download dataset, or manually place dataset in data/processed/"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Dataset downloaded${NC}"
else
    echo -e "${GREEN}✅ Dataset found${NC}"
fi

# Check if model exists
if [ ! -f "models/embedding_model.pkl" ]; then
    echo -e "${YELLOW}⚠️  Trained model not found${NC}"
    echo "Training model (this will take 30-60 seconds)..."
    
    if command -v python3 &> /dev/null; then
        cd training && python3 train_embeddings.py && cd ..
    elif command -v python &> /dev/null; then
        cd training && python train_embeddings.py && cd ..
    else
        echo -e "${RED}❌ Python is not installed${NC}"
        echo "Continuing without trained model (backend will use MockModel)"
    fi
    
    echo -e "${GREEN}✅ Model trained${NC}"
else
    echo -e "${GREEN}✅ Trained model found${NC}"
fi

# Stop any existing containers
echo ""
echo -e "${BLUE}Stopping existing containers...${NC}"
docker-compose down 2>/dev/null || docker compose down 2>/dev/null || true

# Build images
echo ""
echo -e "${BLUE}Building Docker images (this may take a few minutes)...${NC}"
if docker compose version &> /dev/null; then
    docker compose build
else
    docker-compose build
fi

# Start services
echo ""
echo -e "${BLUE}Starting services...${NC}"
if docker compose version &> /dev/null; then
    docker compose up -d
else
    docker-compose up -d
fi

# Wait for services to be healthy
echo ""
echo -e "${BLUE}Waiting for services to be ready...${NC}"
echo "This may take 30-60 seconds for first startup..."

MAX_WAIT=120
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    if docker ps | grep -q "recommender-backend.*healthy" && \
       docker ps | grep -q "recommender-redis.*healthy" && \
       docker ps | grep -q "recommender-mlflow.*healthy"; then
        echo -e "${GREEN}✅ All services are healthy!${NC}"
        break
    fi
    
    echo -n "."
    sleep 2
    ELAPSED=$((ELAPSED + 2))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo -e "${RED}❌ Services did not become healthy in time${NC}"
    echo "Check logs with: docker-compose logs"
    exit 1
fi

# Print status
echo ""
echo -e "${GREEN}"
echo "============================================"
echo "✅ System is running!"
echo "============================================"
echo -e "${NC}"

echo "Services:"
echo -e "${GREEN}  • Frontend:${NC}  http://localhost:3000"
echo -e "${GREEN}  • Backend:${NC}   http://localhost:8000"
echo -e "${GREEN}  • MLflow:${NC}    http://localhost:5000"
echo -e "${GREEN}  • Redis:${NC}     localhost:6379"

echo ""
echo "API Endpoints:"
echo "  • Health:         http://localhost:8000/health"
echo "  • Recommendations: http://localhost:8000/recommend?user_id=1&limit=10"
echo "  • Events:         http://localhost:8000/events (POST)"
echo "  • Metrics:        http://localhost:8000/metrics"

echo ""
echo "Useful commands:"
echo -e "${YELLOW}  docker-compose logs -f${NC}           # View all logs"
echo -e "${YELLOW}  docker-compose logs -f backend${NC}   # View backend logs"
echo -e "${YELLOW}  docker-compose ps${NC}                # Check service status"
echo -e "${YELLOW}  docker-compose down${NC}              # Stop all services"
echo -e "${YELLOW}  docker-compose restart backend${NC}   # Restart backend"

echo ""
echo -e "${BLUE}Test the system:${NC}"
echo "  curl http://localhost:8000/health"
echo "  curl http://localhost:8000/recommend?user_id=1&limit=5"

echo ""
echo -e "${GREEN}Setup complete! 🎉${NC}"
