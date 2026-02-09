# Makefile for Real-Time Recommender System
# Convenience commands for Docker and local development

.PHONY: help install setup train test docker-build docker-up docker-down docker-logs docker-clean

# Default target
.DEFAULT_GOAL := help

# Colors
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

##@ General

help: ## Show this help message
	@echo "$(BLUE)Real-Time Recommender System - Make Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make $(GREEN)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BLUE)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup

install: ## Install Python dependencies
	@echo "$(BLUE)Installing Python dependencies...$(NC)"
	pip install -r backend/requirements.txt
	pip install -r training/requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

install-frontend: ## Install frontend dependencies
	@echo "$(BLUE)Installing frontend dependencies...$(NC)"
	cd frontend && npm install
	@echo "$(GREEN)✓ Frontend dependencies installed$(NC)"

setup: install ## Complete setup (download dataset + train model)
	@echo "$(BLUE)Setting up system...$(NC)"
	@$(MAKE) download-dataset
	@$(MAKE) train

##@ Dataset

download-dataset: ## Download MovieLens-100K dataset
	@echo "$(BLUE)Downloading dataset...$(NC)"
	cd data && python download_dataset.py
	@echo "$(GREEN)✓ Dataset downloaded to data/processed/$(NC)"

check-dataset: ## Verify dataset exists
	@if [ -f data/processed/interactions.csv ]; then \
		echo "$(GREEN)✓ Dataset found (data/processed/)$(NC)"; \
	else \
		echo "$(RED)✗ Dataset not found$(NC)"; \
		echo "Run: make download-dataset"; \
		exit 1; \
	fi

##@ Training

train: check-dataset ## Train ML model
	@echo "$(BLUE)Training model (30-60 seconds)...$(NC)"
	cd training && python train_embeddings.py
	@echo "$(GREEN)✓ Model trained and saved to models/$(NC)"

check-model: ## Verify trained model exists
	@if [ -f models/embedding_model.pkl ]; then \
		echo "$(GREEN)✓ Trained model found$(NC)"; \
	else \
		echo "$(RED)✗ Trained model not found$(NC)"; \
		echo "Run: make train"; \
		exit 1; \
	fi

##@ Testing

test: ## Run system tests
	@echo "$(BLUE)Running system tests...$(NC)"
	python test_system.py

test-training: ## Test training pipeline
	@echo "$(BLUE)Testing training pipeline...$(NC)"
	python test_training.py

test-all: test test-training ## Run all tests

##@ Docker

docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	docker-compose build
	@echo "$(GREEN)✓ Images built$(NC)"

docker-up: ## Start all Docker services
	@echo "$(BLUE)Starting services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo ""
	@echo "$(YELLOW)Services:$(NC)"
	@echo "  Frontend:  http://localhost:3000"
	@echo "  Backend:   http://localhost:8000"
	@echo "  MLflow:    http://localhost:5000"
	@echo "  Redis:     localhost:6379"

docker-dev: ## Start in development mode (hot reload)
	@echo "$(BLUE)Starting in development mode...$(NC)"
	docker-compose -f docker-compose.yml -f docker-compose.override.yml up

docker-down: ## Stop all Docker services
	@echo "$(BLUE)Stopping services...$(NC)"
	docker-compose down
	@echo "$(GREEN)✓ Services stopped$(NC)"

docker-restart: ## Restart all Docker services
	@$(MAKE) docker-down
	@$(MAKE) docker-up

docker-logs: ## View Docker logs
	docker-compose logs -f

docker-logs-backend: ## View backend logs
	docker-compose logs -f backend

docker-logs-frontend: ## View frontend logs
	docker-compose logs -f frontend

docker-ps: ## Show running containers
	docker-compose ps

docker-clean: ## Remove all containers, volumes, and images
	@echo "$(RED)⚠️  This will delete all Docker data$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker-compose down -v; \
		docker system prune -a --volumes -f; \
		echo "$(GREEN)✓ Docker cleaned$(NC)"; \
	fi

##@ Local Development

run-backend: check-model ## Run backend locally
	@echo "$(BLUE)Starting backend...$(NC)"
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

run-frontend: ## Run frontend locally
	@echo "$(BLUE)Starting frontend...$(NC)"
	cd frontend && npm run dev

##@ Utilities

clean: ## Clean Python cache files
	@echo "$(BLUE)Cleaning cache files...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@echo "$(GREEN)✓ Cache cleaned$(NC)"

format: ## Format Python code with black
	@echo "$(BLUE)Formatting code...$(NC)"
	black backend/app training/
	@echo "$(GREEN)✓ Code formatted$(NC)"

lint: ## Lint Python code with flake8
	@echo "$(BLUE)Linting code...$(NC)"
	flake8 backend/app training/ --max-line-length=120
	@echo "$(GREEN)✓ Linting complete$(NC)"

##@ Quick Commands

quick-start: setup docker-build docker-up ## Full setup and start (one command)
	@echo ""
	@echo "$(GREEN)🎉 System is running!$(NC)"
	@echo ""
	@echo "Test it:"
	@echo "  curl http://localhost:8000/health"
	@echo "  curl 'http://localhost:8000/recommend?user_id=1&limit=5'"
	@echo ""
	@echo "Open browser:"
	@echo "  Frontend: http://localhost:3000"
	@echo "  MLflow:   http://localhost:5000"

status: ## Show system status
	@echo "$(BLUE)System Status:$(NC)"
	@echo ""
	@if [ -d data/processed ]; then \
		echo "$(GREEN)✓$(NC) Dataset: data/processed/ (9MB)"; \
	else \
		echo "$(RED)✗$(NC) Dataset: Not found"; \
	fi
	@if [ -f models/embedding_model.pkl ]; then \
		echo "$(GREEN)✓$(NC) Model: models/embedding_model.pkl"; \
	else \
		echo "$(RED)✗$(NC) Model: Not trained"; \
	fi
	@echo ""
	@echo "Docker Services:"
	@docker-compose ps 2>/dev/null || echo "  (not running)"
