#!/bin/bash
# Quick verification script for system readiness

set -e

echo "🚀 Real-Time Recommender MLOps - System Verification"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_command() {
    if command -v $1 &> /dev/null; then
        echo -e "${GREEN}✓${NC} $1 is installed"
        return 0
    else
        echo -e "${RED}✗${NC} $1 is NOT installed"
        return 1
    fi
}

check_port() {
    if lsof -Pi :$1 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠${NC} Port $1 is in use"
        return 1
    else
        echo -e "${GREEN}✓${NC} Port $1 is available"
        return 0
    fi
}

echo "📋 Checking dependencies..."
echo ""

# Check Docker
check_command docker
DOCKER_OK=$?

# Check Docker Compose
check_command docker-compose || check_command "docker compose"
COMPOSE_OK=$?

# Check Python
check_command python3
PYTHON_OK=$?

# Check Node
check_command node
NODE_OK=$?

echo ""
echo "🔌 Checking port availability..."
echo ""

# Check ports
check_port 3000
PORT_3000=$?

check_port 8000
PORT_8000=$?

check_port 5000
PORT_5000=$?

check_port 6379
PORT_6379=$?

echo ""
echo "📂 Checking project structure..."
echo ""

# Check key directories
if [ -d "backend" ]; then
    echo -e "${GREEN}✓${NC} backend/ directory exists"
else
    echo -e "${RED}✗${NC} backend/ directory missing"
fi

if [ -d "frontend" ]; then
    echo -e "${GREEN}✓${NC} frontend/ directory exists"
else
    echo -e "${RED}✗${NC} frontend/ directory missing"
fi

if [ -f "docker-compose.yml" ]; then
    echo -e "${GREEN}✓${NC} docker-compose.yml exists"
else
    echo -e "${RED}✗${NC} docker-compose.yml missing"
fi

if [ -f "requirements.txt" ]; then
    echo -e "${GREEN}✓${NC} requirements.txt exists"
else
    echo -e "${RED}✗${NC} requirements.txt missing"
fi

echo ""
echo "=================================================="

# Summary
if [ $DOCKER_OK -eq 0 ] && [ $COMPOSE_OK -eq 0 ]; then
    echo -e "${GREEN}✓ System is ready!${NC}"
    echo ""
    echo "Run: ${YELLOW}docker-compose up -d${NC}"
    echo "Then visit: ${YELLOW}http://localhost:3000${NC}"
    exit 0
else
    echo -e "${RED}✗ System is NOT ready${NC}"
    echo ""
    echo "Please install missing dependencies:"
    if [ $DOCKER_OK -ne 0 ]; then
        echo "  - Docker: https://docs.docker.com/get-docker/"
    fi
    if [ $COMPOSE_OK -ne 0 ]; then
        echo "  - Docker Compose: https://docs.docker.com/compose/install/"
    fi
    exit 1
fi
