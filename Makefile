# =============================================================================
# Makefile for GitHub Gists API
# =============================================================================
PORT ?= 8080
LOG_LEVEL ?= DEBUG
APP_NAME := gist-api
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
BUILD_TIME := $(shell date -u +"%Y-%m-%dT%H:%M:%SZ")
GIT_SHA := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")
DOCKER_REGISTRY ?= ghcr.io
IMAGE_NAME := $(DOCKER_REGISTRY)/$(APP_NAME):$(VERSION)
IMAGE_SHA := $(DOCKER_REGISTRY)/$(APP_NAME):sha-$(GIT_SHA)
IMAGE_LATEST := $(DOCKER_REGISTRY)/$(APP_NAME):latest

# Docker BuildKit for parallel builds and better caching though in newer Docker versions enabled by default
DOCKER_BUILDKIT := 1
export DOCKER_BUILDKIT

# Python configuration
PYTHON := python3
VENV := .venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
CYAN := \033[0;36m
NC := \033[0m

.PHONY: help install test run clean docker-build docker-run docker-stop format all

# =============================================================================
# Default target
# =============================================================================
help: ## Show this help message
	@echo "$(CYAN)GitHub Gists API - Makefile Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(YELLOW)%-25s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(CYAN)Examples:$(NC)"
	@echo "  make all          # Run all tests with coverage"
	@echo "  make docker-build docker-run # Build Docker image with BuildKit and run the image"

# =============================================================================
# Local Development
# =============================================================================
install: $(VENV) ## Create virtual environment and install dependencies
	@echo "$(GREEN)Installing dependencies...$(NC)"
	$(PIP) install --upgrade pip -q
	$(PIP) install -e ".[dev]" -q

$(VENV):
	@echo "$(GREEN)Creating virtual environment...$(NC)"
	$(PYTHON) -m venv $(VENV)

test: install ## Run all tests with coverage
	@echo "$(GREEN)Running tests with coverage...$(NC)"
	PYTHONPATH=src $(PYTEST) \
		--cov=src \
		--cov-report=term-missing \
		--cov-report=html \
		--cov-fail-under=80

format: install ## Format code with Ruff
	@echo "$(GREEN)Formatting code...$(NC)"
	$(VENV)/bin/ruff format src/ tests/
	$(VENV)/bin/ruff check src/ tests/ --fix


run: install ## Run the development server
	@echo "$(GREEN)Starting development server on port $(PORT) with LOG_LEVEL=$(LOG_LEVEL)...$(NC)"
	PYTHONPATH=src LOG_LEVEL=$(LOG_LEVEL) $(VENV)/bin/uvicorn main:app --host 0.0.0.0 --port $(PORT) --reload

# =============================================================================
# Docker Build & Run
# =============================================================================
docker-build: ## Build Docker image with BuildKit (production-ready)
	@echo "$(GREEN)Building Docker image: $(IMAGE_SHA)$(NC)"
	docker build \
		--build-arg BUILDKIT_INLINE_CACHE=1 \
		--build-arg PORT=$(PORT) \
		--build-arg VERSION=$(VERSION) \
		--build-arg BUILD_TIME=$(BUILD_TIME) \
		--build-arg REVISION=$(GIT_SHA) \
		--tag $(IMAGE_SHA) \
		--tag $(IMAGE_LATEST) \
		--progress=plain \
		--platform linux/amd64 \
		.
	@echo "$(GREEN)Image built successfully:$(NC)"
	@docker images "$(DOCKER_REGISTRY)/$(APP_NAME):latest" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

docker-run: docker-stop ## Run Docker container with security hardening
	@echo "$(GREEN)Running container on port $(PORT)...$(NC)"
	docker run -d \
		--name $(APP_NAME) \
		--publish $(PORT):$(PORT) \
		--read-only \
		--tmpfs /tmp \
		--security-opt no-new-privileges:true \
		--cap-drop ALL \
		--health-cmd "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:$(PORT)/health', timeout=5)\"" \
		--health-interval 30s \
		--health-timeout 10s \
		--health-retries 3 \
		--env LOG_LEVEL=$(LOG_LEVEL) \
		$(IMAGE_LATEST)
	@echo "$(GREEN)Container started.$(NC)"
	@echo "$(CYAN)Health: http://localhost:$(PORT)/health$(NC)"
	@echo "$(CYAN)API:    http://localhost:$(PORT)/octocat$(NC)"
	@echo "$(CYAN)Swagger API:    http://localhost:$(PORT)/docs$(NC)"

docker-stop: ## Stop and remove Docker container
	@docker stop $(APP_NAME) 2>/dev/null || true
	@docker rm $(APP_NAME) 2>/dev/null || true

docker-logs: ## Show Docker container logs
	docker logs -f $(APP_NAME)


# =============================================================================
# Security
# =============================================================================
TRIVY_VERSION := v0.69.3
TRIVY_INSTALL_DIR := /usr/local/bin

.PHONY: install-trivy
install-trivy: ## Install Trivy vulnerability scanner (v0.69.3) to /usr/local/bin
	@if command -v trivy >/dev/null 2>&1; then \
		echo "$(GREEN)trivy already installed: $$(trivy --version | head -1)$(NC)"; \
	else \
		echo "$(YELLOW)trivy not found. Installing $(TRIVY_VERSION) to $(TRIVY_INSTALL_DIR)...$(NC)"; \
		curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh \
			| sudo sh -s -- -b $(TRIVY_INSTALL_DIR) $(TRIVY_VERSION); \
		echo "$(GREEN)trivy installed: $$(trivy --version | head -1)$(NC)"; \
	fi

security-scan: docker-build install-trivy ## Scan Docker image for vulnerabilities (auto-installs trivy if missing)
	@echo "$(YELLOW)Running security scan (ignoring accepted risks documented in .trivyignore)...$(NC)"
	trivy image --severity HIGH,CRITICAL --ignorefile .trivyignore $(IMAGE_LATEST)


smoke-test: ## Run smoke tests against running container
	@echo "$(GREEN)Running smoke tests...$(NC)"
	@curl -sf http://localhost:$(PORT)/health || { echo "$(RED)Health check failed$(NC)"; exit 1; }
	@curl -sf http://localhost:$(PORT)/octocat?per_page=1 || { echo "$(RED)API endpoint failed$(NC)"; exit 1; }
	@echo "$(GREEN)Smoke tests passed!$(NC)"

# =============================================================================
# Cleanup
# =============================================================================
clean: docker-stop ## Clean up all build artifacts
	@echo "$(GREEN)Cleaning up...$(NC)"
	rm -rf $(VENV)
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf src/__pycache__
	rm -rf tests/__pycache__
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	rm -rf src/*.egg-info/
	rm -rf build/
	rm -rf dist/
	rm -f coverage.xml .coverage
	docker rmi $(IMAGE_SHA) $(IMAGE_LATEST) 2>/dev/null || true

# =============================================================================
# Quick Commands
# =============================================================================
.PHONY: quick
quick: install test ## Quick development test (install + test)

all: clean install format test docker-build docker-run ## Full clean build and test