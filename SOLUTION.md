## Table of Contents
- [Introduction](#introduction)
- [Features](#features)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
  - [Option 1: Makefile (Recommended)](#option-1-makefile-recommended)
  - [Option 2: Docker](#option-2-docker)
  - [Option 3: Manual Setup](#option-3-manual-setup)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Running Tests](#running-tests)
- [Makefile Commands](#makefile-commands)
- [Security](#security)
- [Working Solution Steps](#working-solution)

---

# Introduction

A production-grade FastAPI service that retrieves publicly available GitHub Gists for any user via a clean, paginated REST API. Built with security hardening, structured logging, in-memory caching, and a full Docker image build process baked in.

Make as a build tool is used for build automation of the project for simplicity and ease of use, so please install it using below command.
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
It is not mandatory to use make. We can use docker commands directly to build and run the project. Screenshots for the working project is captured in section [Working Solution Steps](#working-solution).
####  Note: If tests fail because of Github rate limit then please export GITHUB Personal Access Token.
```
export GITHUB_TOKEN="github_pat_Xxxxxxxxxxxxxxxx" 
```


## Features

| Feature | Detail |
|---------|--------|
| **REST API** | `GET /<username>` returns paginated public Gists |
| **Pagination** | `page` and `per_page` query parameters |
| **Caching** | In-memory cache with 5-minute TTL (per username + page combination) |
| **Structured Logging** | JSON-formatted logs for easy ingestion by log aggregators |
| **Docker** | Multi-stage build with a minimal, hardened production image (~150 MB) |
| **Security** | Non-root user, read-only filesystem, capability dropping |
| **CI/CD** | GitHub Actions – lint → test → build → security scan → deploy |
| **Observability** | Health-check endpoint, structured logs, Docker HEALTHCHECK |

---

## Project Structure

```
.
├── src/
│   ├── __init__.py          # Package metadata and version
│   ├── api.py               # API route definitions and handlers
│   ├── cache.py             # In-memory caching logic
│   ├── config.py            # Environment settings and structured logging setup
│   ├── github_client.py     # External client for GitHub API interaction
│   ├── main.py              # Application entry point and startup orchestration
│   ├── models.py            # Pydantic models for API responses
│
├── tests/
│   ├── __init__.py 
│   └── test_main.py             # Unit tests against live GitHub API
│
├── .github/
│   └── workflows/
│       ├── ci.yml               # CI Pipeline (Lint → Test → Docker Build)
│
├── .dockerignore                # Excludes dev artefacts from Docker context
├── .env.example                 # Template for local environment variables
├── .gitignore
├── Dockerfile                   # Multi-stage Docker build for production
├── Makefile                     # Developer convenience and automation commands
├── pyproject.toml               # Dependency and build system configuration
└── README.md                    # Project completion guidelines
└── SOLUTION.md                  # Solution description and steps to run the project
```

### Key Source Files

| File | Responsibility |
|------|----------------|
| `src/main.py` | Application entry point and FastAPI orchestration |
| `src/api.py` | Core route handlers and business logic wiring |
| `tests/test_main.py` | Real-world integration tests against the live GitHub API |
| `Dockerfile` | Multi-stage Docker build for a hardened production image |
| `Makefile` | Build automation and developer convenience commands |

---

## Prerequisites

| Tool | Minimum Version | Purpose |
|------|-----------------|---------|
| Python | 3.9+ | Runtime |
| pip / venv | bundled with Python | Dependency management |
| Docker | 20.10+ (BuildKit enabled) | Container build and run |
| GNU Make | any | Makefile convenience targets |
| curl | any | Smoke tests / manual API calls |
| trivy *(optional)* can be installed through Makefile itself | latest | Local vulnerability scanning |

> **macOS note:** Docker Desktop ships with BuildKit enabled by default. On Linux, set `DOCKER_BUILDKIT=1` (already done in the Makefile).

---

## Quick Start

### Option 1: Makefile (Recommended)

The Makefile manages the virtual environment automatically — you do not need to activate it manually.

```bash
# 1. Clone the repo
git clone <repository-url>
cd <repository-directory>

# 2. (Optional) Configure GitHub token for higher rate limits
cp .env.example .env
# Edit .env and set GITHUB_TOKEN=<your-pat>

# 3. Install dependencies into .venv/
make install

# 4. Run all tests (unit + integration) with ≥80% coverage gate
make test

# 5. Start the development server with hot-reload on port 8080
make run

# 6. Run entire step of clean, install, test, build and run using docker instead of step 2-5. Currently does not implement tagging with git SHA but recommended for Production
make all 
```

The API is now available at `http://localhost:8080` 

SWAGGER Document is now available at `http://localhost:8080/docs`

HEALTH Endpoint is now available at `http://localhost:8080/health`

```bash
# Verify health
curl http://localhost:8080/health

# Fetch gists for the 'octocat' GitHub user
curl http://localhost:8080/octocat

# Paginated request
curl "http://localhost:8080/octocat?page=2&per_page=10"
```

---

### Option 2: Docker

```bash
# Build the image (uses BuildKit for layer caching)
make docker-build

# Run with all security hardening flags applied
make docker-run

# Check logs
make docker-logs

# Stop and remove the container
make docker-stop
```

Or run it manually with the full set of security flags:

```bash
docker build -t gist-api:latest .

docker run -d \
  --name gist-api \
  --publish 8080:8080 \
  --read-only \
  --tmpfs /tmp \
  --security-opt no-new-privileges:true \
  --cap-drop ALL \
  gist-api:latest
```

Verify the container is healthy:

```bash
docker ps                              # STATE should show "(healthy)" after ~30s
curl http://localhost:8080/health      # {"status": "healthy"}
curl http://localhost:8080/octocat     # JSON array of gists
```

---

### Option 3: Manual Setup

If you prefer full control without Make, then from the repo root follow the below instructions.

```bash
# Create and activate a virtual environment
python3 -m venv .venv && source .venv/bin/activate

# Install package in editable mode with dev extras
pip install .

# Run the development server hot-reload)
PYTHONPATH=src uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in as needed:

```bash
cp .env.example .env
```

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `GITHUB_TOKEN` | *(empty)* | No | GitHub Personal Access Token. Increases the API rate limit from **60 req/hour** (unauthenticated) to **5,000 req/hour**. Create one at [github.com/settings/tokens](https://github.com/settings/tokens) — no scopes needed for public data. |
| `PORT` | `8080` | No | TCP port the Uvicorn server listens on. |
| `LOG_LEVEL` | `DEBUG` | No | Logging level for the application (e.g., DEBUG, INFO, WARNING, ERROR). |

---

## API Reference

### `GET /<username>`

Returns a simplified list of the specified GitHub user's public Gists.

**Path parameter**

| Parameter | Type | Description |
|-----------|------|-------------|
| `username` | string | GitHub username |

**Query parameters**

| Parameter | Type | Default | Constraints | Description |
|-----------|------|---------|-------------|-------------|
| `page` | integer | `1` | ≥ 1 | Page number |
| `per_page` | integer | `30` | 1 – 100 | Items per page |

**Example request**

```bash
curl "http://localhost:8080/octocat?page=1&per_page=1"
```

**Example response** `200 OK`

```json
[
  {
    "id": "aa5a315d61ae9438b18d",
    "url": "https://gist.github.com/aa5a315d61ae9438b18d",
    "description": "My first gist",
    "created_at": "2024-01-15T10:30:00Z",
    "files_count": 2
  }
]
```

**Error responses**

| Status | Scenario |
|--------|----------|
| `404 Not Found` | GitHub user does not exist |
| `422 Unprocessable Entity` | Invalid query parameter values |
| `5xx` | GitHub API error or internal server error |

---

### `GET /health`

Health-check endpoint used by container orchestration (Docker, Kubernetes liveness/readiness probes).

```bash
curl http://localhost:8080/health
# {"status": "healthy"}
```

### Interactive API Docs

While the server is running, open:

- **Swagger UI** → [http://localhost:8080/docs](http://localhost:8080/docs)
- **ReDoc** → [http://localhost:8080/redoc](http://localhost:8080/redoc)

![Swagger UI](/.images/swagger_validation.png)

---

## Running Tests

```bash
# All tests with HTML coverage report
make test

# Check linting without fixing
make lint

# Auto-fix linting issues and format code
make format
```

The test suite performs real-world validation against the live GitHub API for a deterministic and accurate end-to-end test. It does not use mocks.

---

## Makefile Commands

```bash
make help           # Print all commands with descriptions
```

| Command | Description |
|---------|-------------|
| `make install` | Create `.venv` and install all dependencies |
| `make test` | Run all real-world integration tests with ≥80% branch coverage gate |
| `make format` | Auto-format and fix lint issues with Ruff |
| `make run` | Start dev server on port 8080 with `--reload` |
| `make docker-build` | Build production Docker image with BuildKit |
| `make docker-run` | Run container with security hardening flags |
| `make docker-stop` | Stop and remove the running container |
| `make docker-logs` | Tail container logs |
| `make install-trivy` | Auto-install Trivy v0.69.3 to `/usr/local/bin` (skips if already present) |
| `make security-scan` | Build image, auto-install Trivy if missing, then scan for HIGH/CRITICAL CVEs |
| `make smoke-test` | Curl health + octocat endpoints against running container |
| `make clean` | Remove `.venv`, caches, coverage files, Docker images |
| `make all` | Clean full build: clean → install → format → test → docker-build |

---

## Security

### Current Hardening (Container Runtime)

| Control | How It Is Applied |
|---------|------------------|
| Non-root user | `useradd -u 10001`; `USER appuser` in Dockerfile |
| Read-only root filesystem | `--read-only` flag in `docker run` / `make docker-run` |
| Capability dropping | `--cap-drop ALL` removes all Linux capabilities |
| No privilege escalation | `--security-opt no-new-privileges:true` |
| Minimal base image | `python:3.9-slim` — no shell, no package manager in prod stage |
| Vulnerability scanning | Trivy scans for CRITICAL/HIGH CVEs in CI (`make security-scan`) |
| Dependency pinning | Version ranges in `pyproject.toml`; lock files can be generated with `pip-compile` |

## Working Solution

### 1.  Make Command

![Health Check](/.images/make.png)

### 2. API Build

![Gist API](/.images/make_build.png)

### 3. Smoke Test

![Smoke Test](/.images/smoke_test_validate.png)

### 3. Validate Through Swagger

![Swagger Validation](/.images/swagger_validation.png)

### 4. Run API Locally without Docker with Python installed
![Run Api Locally](/.images/local_server.png)
