# CI/CD Bootstrap Prompt

> **Usage:** Copy this entire prompt and run it against any branch that already has the Python app source code (`src/`, `tests/`, `pyproject.toml`, `Dockerfile`, `Makefile`) but no CI/CD, Helm, or ArgoCD setup. It will generate all workflows, Helm charts, and the ArgoCD ApplicationSet.

---

## The Prompt

```
You are a senior DevSecOps engineer. I have a Python FastAPI application in this repository.
The app source lives in `src/` with tests in `tests/` and dependencies defined in `pyproject.toml`.
The Dockerfile and Makefile already exist — DO NOT create or modify them.

Generate a COMPLETE production-grade CI/CD pipeline with GitOps deployment.
Create ALL of the files listed below with EXACTLY the structure and content described.
Do NOT skip any file. Do NOT use placeholder comments — write full, working content for every file.

## REPO CONTEXT

- **App name:** gist-api
- **Language:** Python 3.12, FastAPI + Uvicorn
- **Package manager:** pip with pyproject.toml (setuptools backend)
- **Docker registry:** DockerHub (username stored in `DOCKERHUB_USERNAME` secret, token in `DOCKERHUB_TOKEN` secret)
- **Registry prefix:** hemant1 (so images are `hemant1/gist-api:<tag>`)
- **Git hosting:** GitHub (PAT stored in `TOKEN_GITHUB` secret)
- **GitOps tool:** ArgoCD watching the `main` branch
- **Git repo URL:** git@github.com:hemuku90/python-ci-cd.git
- **Environments:** dev → qa → staging → prod
- **K8s namespaces:** gist-api-dev, gist-api-qa, gist-api-staging, gist-api-prod

---

## FILE 1: `.github/workflows/ci.yml`

Create a CI workflow triggered on:
- `pull_request` to main (opened, synchronize, reopened, ready_for_review)
- `push` to main
- `workflow_dispatch`

Set concurrency group: `${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}` with cancel-in-progress.
Env: PYTHON_VERSION: '3.12'
Permissions: contents: read, pull-requests: write

### Jobs (7 total):

**1. lint-and-format** — Lint & Format
- Checkout (pin actions/checkout to commit SHA v4.2.2: `@11bd71901bbe5b1630ceea73d27597364c9af683`)
- Setup Python (pin actions/setup-python to SHA v5.6.0: `@a26af69be951a213d495a4c3e4e4022e16d87065`) with pip cache
- Install ruff + flake8
- Run: `ruff check src/ tests/`, `ruff format --check src/ tests/`, `flake8 src/ tests/ --max-line-length=120`

**2. security-sast** — SAST Scan (Bandit)
- Install bandit, run: `bandit -r src/ -f screen -ll --exclude tests/,venv/`

**3. secret-scan** — Secret Detection
- Checkout with fetch-depth: 0 (full history)
- Use `gitleaks/gitleaks-action@ff98106e4c7b2bc287b24eaf42907196329070c7` (v2.3.9)

**4. dependency-scan** — Dependency Scan
- Install safety, install project if pyproject.toml exists, run `safety check --full-report`
- `continue-on-error: true` with comment "for now we are ignoring the dependency vulnerabilities"

**5. unit-tests** — Unit Tests (timeout: 15min)
- Install `pip install -e ".[dev]"`
- Run: `pytest tests/ --cov=src --cov-report=xml --cov-fail-under=80 --junitxml=junit.xml`
- Upload coverage.xml and junit.xml as artifacts (retention: 7 days)
- Pin actions/upload-artifact to SHA v4.6.2: `@ea165f8d65b6e75b540449e92b4886f43607fa02`

**6. integration-tests** — Integration Tests (Mock)
- `needs: unit-tests`
- Echo mock messages about testing API endpoints, DB connectivity, cache layer

**7. license-compliance** — License Compliance (Mock)
- No dependencies (runs in parallel)
- Echo mock messages about scanning for GPL/AGPL/SSPL, validating allowlist

ALL checkout steps must use `token: ${{ secrets.TOKEN_GITHUB }}`.
ALL jobs must have `timeout-minutes` and explicit `permissions: contents: read`.

---

## FILE 2: `.github/workflows/build.yml`

Create a Build & Deploy workflow triggered on:
- `push` tags matching `v*`
- `workflow_dispatch`

Set concurrency group: `${{ github.workflow }}-${{ github.ref }}` with cancel-in-progress.
Env: PYTHON_VERSION: '3.12', IMAGE_NAME: 'gist-api', DOCKER_REGISTRY: 'hemant1'
Permissions: contents: read, id-token: write

### Jobs (5 total):

**1. build-and-push** — Build & Push (timeout: 30min)
- Permissions: contents: read, id-token: write
- Output: `tag_name` from prep step
- Steps:
  - Checkout with fetch-depth: 0
  - **Prepare Metadata:** If ref is `refs/tags/v*`, extract version; else use `manual-$(date +%s)`
  - **Login to DockerHub** using `docker/login-action@74a5d142397b4f367a81961eba4e8cd7edddf772` (v3.4.0)
  - **Check Image Existence:** `docker manifest inspect` — if exists, skip build
  - **Setup Buildx:** `docker/setup-buildx-action@b5ca514318bd6ebac0fb2aedd5d36ec1b5c232a2` (v3.10.0), conditional on image not existing
  - **Build and Push:** `docker/build-push-action@14487ce63c7a62a4a324b0bfb37086795e31c6c1` (v6.16.0), with GHA cache, conditional
  - **Trivy Scan:** `aquasecurity/trivy-action@master`, format table, severity CRITICAL,HIGH, ignore-unfixed
  - **SBOM Generation (Mock):** Echo mock for `syft <image> -o spdx-json`
  - **Cosign Image Signing (Mock):** Echo mock for `cosign sign --yes $IMAGE` with keyless Sigstore

**2. deploy-dev** — Deploy Dev
- `needs: build-and-push`, environment: dev, permissions: contents: write
- Checkout ref: main, fetch-depth: 0
- **Update Dev Manifest:** sed replace tag in `deploy/helm/gist-api/values-dev.yaml`, git commit with `[skip ci]`, git pull --rebase, git push
- **Smoke Test (Mock):** Echo GET /health → 200, GET /docs → 200, response time
- **Notify (Mock):** Echo Slack notification to #deployments

**3. deploy-qa** — Deploy QA
- `needs: [build-and-push, deploy-dev]`, environment: qa
- Same manifest update pattern for `values-qa.yaml`
- **Smoke Test (Mock)**
- **E2E Tests (Mock):** Echo various API scenarios (POST, GET, auth flow, error handling, 12/12 passed)
- **DAST Scan (Mock):** Echo OWASP ZAP baseline scan results
- **Notify (Mock):** Slack with E2E ✓ DAST ✓

**4. deploy-staging** — Deploy Staging
- `needs: [build-and-push, deploy-qa]`, environment: staging
- Same manifest update for `values-staging.yaml`
- **Smoke Test (Mock)**
- **Load & Performance Test (Mock):** Echo k6 results — p50/p95/p99 latency, RPS, error rate
- **Canary Validation (Mock):** Echo canary weight 10%, error rate, latency delta, promote to 100%
- **Notify (Mock):** Slack with Load ✓ Canary ✓

**5. deploy-prod** — Deploy Prod (MANUAL GATE)
- `needs: [build-and-push, deploy-staging]`, environment: production (configured in GitHub Settings with required reviewers)
- Same manifest update for `values-prod.yaml`
- **Smoke Test (Mock)**
- **Rollback Check (Mock):** Echo ArgoCD rollback readiness, error rate monitoring for 5 min
- **Notify (Mock):** Echo Slack #deployments + #engineering + PagerDuty change event

ALL deploy jobs follow this git commit pattern:
```bash
git config --global user.name "github-actions[bot]"
git config --global user.email "github-actions[bot]@users.noreply.github.com"
git add $MANIFEST
git commit -m "chore(ops): update <env> to $TAG [skip ci]" || echo "No changes"
git pull --rebase origin main
git push origin main
```

---

## FILE 3: `deploy/helm/gist-api/Chart.yaml`

```yaml
apiVersion: v2
name: gist-api
description: A Helm chart for the Gist API
type: application
version: 0.1.0
appVersion: "1.0.0"
```

---

## FILE 4: `deploy/helm/gist-api/values.yaml` (default values)

```yaml
replicaCount: 1

image:
  repository: hemant1/gist-api
  pullPolicy: IfNotPresent
  tag: "latest"

service:
  type: ClusterIP
  port: 80

resources:
  limits:
    cpu: 200m
    memory: 256Mi
  requests:
    cpu: 100m
    memory: 128Mi
```

---

## FILES 5-8: Per-environment values files

Create these four files, each containing only `tag: 1.12.0`:
- `deploy/helm/gist-api/values-dev.yaml`
- `deploy/helm/gist-api/values-qa.yaml`
- `deploy/helm/gist-api/values-staging.yaml`
- `deploy/helm/gist-api/values-prod.yaml`

---

## FILE 9: `deploy/helm/gist-api/templates/_helpers.tpl`

Standard Helm helpers with these named templates:
- `gist-api.name` — defaults to Chart.Name, truncated to 63 chars
- `gist-api.fullname` — handles fullnameOverride, Release.Name contains name check
- `gist-api.chart` — `<name>-<version>` with + replaced by _
- `gist-api.labels` — helm.sh/chart, selectorLabels, app.kubernetes.io/version, managed-by
- `gist-api.selectorLabels` — app.kubernetes.io/name and instance

---

## FILE 10: `deploy/helm/gist-api/templates/deployment.yaml`

Kubernetes Deployment template:
- Uses `gist-api.fullname` for metadata.name
- Uses `gist-api.labels` and `gist-api.selectorLabels`
- replicas: .Values.replicaCount
- Container: name from Chart.Name, image `{{ .Values.image.repository }}:{{ .Values.image.tag }}`
- imagePullPolicy from values
- Container port: 8000 (http, TCP)
- Resources from values (using toYaml | nindent 12)

---

## FILE 11: `deploy/helm/gist-api/templates/service.yaml`

Kubernetes Service template:
- Uses fullname and labels helpers
- Type from .Values.service.type
- Port: .Values.service.port → targetPort 8000
- Selector from selectorLabels

---

## FILE 12: `deploy/argocd/applicationset.yaml`

ArgoCD ApplicationSet:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: gist-api-environments
  namespace: argocd
spec:
  generators:
  - list:
      elements:
        - env: dev
          namespace: gist-api-dev
        - env: qa
          namespace: gist-api-qa
        - env: staging
          namespace: gist-api-staging
        - env: prod
          namespace: gist-api-prod
  template:
    metadata:
      name: 'gist-api-{{env}}'
    spec:
      project: default
      source:
        repoURL: 'git@github.com:hemuku90/python-ci-cd.git'
        targetRevision: main
        path: deploy/helm/gist-api
        helm:
          valueFiles:
            - 'values.yaml'
            - 'values-{{env}}.yaml'
      destination:
        server: 'https://kubernetes.default.svc'
        namespace: '{{namespace}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
```

---

## IMPORTANT RULES

1. **Pin ALL GitHub Actions to full commit SHAs** — never use `@v4`, always use `@<40-char-sha>`.
2. **Every mock step** must include an echo hint like `(mock — replace with: <real command>)`.
3. **Every checkout** must use `token: ${{ secrets.TOKEN_GITHUB }}`.
4. **Every job** must have `timeout-minutes` and explicit `permissions`.
5. **Concurrency** groups must be set on both workflows to prevent duplicate runs.
6. **Deploy jobs** must follow the GitOps pattern: update values file → git commit [skip ci] → rebase → push.
7. **Do NOT create or modify** the Dockerfile or Makefile — they already exist.

Generate ALL 12 files now. Do not ask clarifying questions. Do not skip any file.
```

---

## Directory Structure Created

```
.
├── .github/
│   └── workflows/
│       ├── ci.yml          ← CI pipeline (PR validation)
│       └── build.yml       ← Build + progressive deploy pipeline
└── deploy/
    ├── argocd/
    │   └── applicationset.yaml  ← ArgoCD multi-env setup
    └── helm/
        └── gist-api/
            ├── Chart.yaml
            ├── values.yaml          ← defaults
            ├── values-dev.yaml      ← dev overrides
            ├── values-qa.yaml       ← qa overrides
            ├── values-staging.yaml  ← staging overrides
            ├── values-prod.yaml     ← prod overrides
            └── templates/
                ├── _helpers.tpl
                ├── deployment.yaml
                └── service.yaml
```

## Pipeline Flow

```
┌─────────────────── CI (every PR) ────────────────────┐
│ Lint → SAST → Secrets → Deps → Unit → Integration   │
│                                   License (parallel) │
└──────────────────────────────────────────────────────┘

┌──────────── Build & Deploy (on v* tag) ──────────────┐
│ Build → Trivy → SBOM → Cosign                       │
│   → Dev    (smoke → notify)                          │
│   → QA     (smoke → E2E → DAST → notify)            │
│   → Staging(smoke → load → canary → notify)          │
│   → Prod   [MANUAL] (smoke → rollback → notify)     │
└──────────────────────────────────────────────────────┘

           ArgoCD watches main branch
     values-<env>.yaml tag change → auto-sync
```

## Required GitHub Secrets

| Secret | Purpose |
|--------|---------|
| `TOKEN_GITHUB` | PAT for checkout + git push |
| `DOCKERHUB_USERNAME` | DockerHub login |
| `DOCKERHUB_TOKEN` | DockerHub access token |

## Required GitHub Environments

| Environment | Protection Rules |
|-------------|-----------------|
| `dev` | None (auto-deploy) |
| `qa` | None (auto-deploy) |
| `staging` | None (auto-deploy) |
| `production` | Required reviewers |
