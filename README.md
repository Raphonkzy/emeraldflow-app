# EmeraldFlow App

[![CI/CD Pipeline](https://github.com/Raphonkzy/emeraldflow-app/actions/workflows/ci.yml/badge.svg)](https://github.com/Raphonkzy/emeraldflow-app/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/Docker-Multi--Stage-2496ED?logo=docker&logoColor=white)](./Dockerfiles/app/multistage/Dockerfile)
[![Amazon ECR](https://img.shields.io/badge/Registry-Amazon_ECR-FF9900?logo=amazonaws&logoColor=white)](https://aws.amazon.com/ecr/)
[![Python](https://img.shields.io/badge/Runtime-Python_3.11-3776AB?logo=python&logoColor=white)](./requirements.txt)
[![SonarQube](https://img.shields.io/badge/Quality_Gate-SonarQube-4E9BCD?logo=sonarqube&logoColor=white)](./sonar-project.properties)

## Executive Summary

**`emeraldflow-app`** is the application source repository for the EmeraldFlow platform — a containerized Python/Flask web service deployed on Amazon EKS via a GitOps delivery model.

This repository owns the **full left side of the delivery pipeline**: application code, Docker container definitions, automated testing, static analysis, and the CI workflow that publishes a verified image to Amazon ECR and opens a promotion Pull Request to the downstream Helm repository.

It does **not** own deployment configuration or infrastructure. Those responsibilities are separated into purpose-built repositories (see [Integration Map](#upstream--downstream-integration) below).

---

## Upstream & Downstream Integration

EmeraldFlow follows a three-repository GitOps architecture where concerns are strictly separated.

| Repository | Role | Link |
|---|---|---|
| **`emeraldflow-app`** *(this repo)* | Application source, Docker build, CI pipeline | — |
| **`emeraldflow-helm`** | Helm chart + Argo CD Application manifests (GitOps target) | [Raphonkzy/emeraldflow-helm](https://github.com/Raphonkzy/emeraldflow-helm) |
| **`emeraldflow-infra`** | Terraform — AWS networking, EKS cluster, ECR, IAM | [Raphonkzy/emeraldflow-infra](https://github.com/Raphonkzy/emeraldflow-infra) |

**Delivery flow:**

```
emeraldflow-app  ──►  Amazon ECR  ──►  PR to emeraldflow-helm  ──►  Argo CD  ──►  Amazon EKS
     (CI)                                      (GitOps gate)              (CD)
```

---

## CI/CD Pipeline Architecture

The pipeline is defined in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) and consists of **three sequential jobs** with distinct trigger conditions.

### Trigger Model

| Event | Jobs Activated |
|---|---|
| `pull_request` → `main` | `test-and-sonar` |
| `push` → `main` (merge) | `build-and-push-ecr` → `update-helm-manifest` |

This separation ensures that **code quality is enforced on every PR** and that **container promotion only happens on verified, merged commits**.

---

### Job 1 — Unit Tests & SonarQube Scan

> **Trigger:** `pull_request` to `main`

```
Checkout (fetch-depth: 0)
  │
  ▼
Set up Python 3.11 (pip cache enabled)
  │
  ▼
pip install -r requirements.txt
  │
  ▼
pytest --cov=app --cov-report=xml:coverage.xml tests/
  │
  ▼
SonarQube Scanner (sonarsource/sonarqube-scan-action@v5)
  │     ↳ Reads: sonar-project.properties
  │     ↳ Uploads: coverage.xml as Python coverage report
  ▼
SonarQube Quality Gate (sonarsource/sonarqube-quality-gate-action@v1.1.0)
      ↳ Timeout: 5 minutes
      ↳ FAILS the PR if the gate does not pass — blocks merge
```

**Key configuration in [`sonar-project.properties`](./sonar-project.properties):**
- `sonar.projectKey` = `emeraldflow-app`
- `sonar.language` = `py`
- `sonar.python.coverage.reportPaths` = `coverage.xml`
- Excludes: `.venv/`, `tests/`, `__pycache__/`, `*.pyc`, `migrations/`

---

### Job 2 — Build & Push to Amazon ECR

> **Trigger:** `push` to `main`

```
Checkout repository
  │
  ▼
Configure AWS Credentials (aws-actions/configure-aws-credentials@v4)
  │     ↳ Reads: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
  ▼
Log in to Amazon ECR (aws-actions/amazon-ecr-login@v2)
  │
  ▼
Set image tag → github.sha (full commit SHA)
  │
  ▼
docker build -f Dockerfiles/app/multistage/Dockerfile .
  │     ↳ Tag 1: $ECR_REGISTRY/$ECR_REPOSITORY:<commit-sha>
  │     ↳ Tag 2: $ECR_REGISTRY/$ECR_REPOSITORY:latest
  ▼
docker push (both tags) → Amazon ECR
```

The image tag is the **full Git commit SHA** (`github.sha`), providing a direct, immutable link between every running container and its source commit.

---

### Job 3 — Update Helm Manifest (GitOps Promotion)

> **Trigger:** `push` to `main` | **Requires:** Job 2 to succeed (`needs: build-and-push-ecr`)

```
Checkout emeraldflow-helm repo
  │     ↳ Uses: HELM_REPO_ACCESS_TOKEN (PAT with repo write access)
  │     ↳ Target path: helm-repo/
  ▼
sed update: image.tag → <new-commit-sha> in values.yaml
  │     ↳ Primary path: helm/emeraldflow/values.yaml
  │     ↳ Fallback: auto-discovers first values.yaml if path differs
  ▼
peter-evans/create-pull-request@v6
      ↳ Branch: promote-image-<commit-sha>
      ↳ Title: "Promote App Image: <commit-sha>"
      ↳ Base: main
      ↳ Merge triggers Argo CD sync → rolling deploy on EKS
```

This job enforces a **manual production approval gate**: no image is deployed to the cluster without a human reviewing and merging the Helm PR. Argo CD detects the merge and initiates the rollout.

---

## Required Secrets & Environment Variables

Configure these in **Settings → Secrets and variables → Actions** in this repository.

### Secrets (`secrets.*`)

| Secret Name | Description | Required By |
|---|---|---|
| `AWS_ACCESS_KEY_ID` | IAM access key for ECR authentication | Job 2 |
| `AWS_SECRET_ACCESS_KEY` | IAM secret key for ECR authentication | Job 2 |
| `SONAR_TOKEN` | SonarQube user token for scanner auth and Quality Gate polling | Job 1 |
| `HELM_REPO_ACCESS_TOKEN` | GitHub PAT with `repo` scope — write access to `emeraldflow-helm` | Job 3 |
| `GITOPS_PAT` | Fallback alias for `HELM_REPO_ACCESS_TOKEN` (either name is accepted) | Job 3 |

### Repository Variables (`vars.*`)

| Variable Name | Description | Required By |
|---|---|---|
| `SONAR_HOST_URL` | Full URL of your SonarQube instance (e.g. `https://sonar.example.com`) | Job 1 |
| `AWS_REGION` | AWS region where ECR is hosted (e.g. `ap-southeast-1`) | Job 2 |
| `ECR_REPOSITORY` | ECR repository name (e.g. `emeraldflow-app`) | Job 2 |

> **Note:** `SONAR_HOST_URL` and `AWS_REGION` are stored as **Variables** (non-secret), not Secrets. The workflow reads them via `${{ vars.* }}`.

---

## Application Endpoints

The Flask application ([`app.py`](./app.py)) exposes three HTTP routes:

| Endpoint | Method | Description |
|---|---|---|
| `/` | `GET` | Renders the EmeraldFlow landing UI |
| `/health` | `GET` | Liveness probe — returns `{"status": "UP", "service": "emeraldflow-app"}` |
| `/db-status` | `GET` | Database connectivity check — connects to MySQL via PyMySQL |

The application is served by **Gunicorn** and binds to `0.0.0.0:8080` by default.

### Runtime Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `emeralddb` | MySQL hostname |
| `DB_USER` | `root` | MySQL username |
| `DB_PASSWORD` | *(empty)* | MySQL password — inject via Kubernetes Secret |
| `DB_NAME` | `accounts` | MySQL database name |
| `PORT` | `8080` | Application listen port |

---

## Local Development & Testing

### Run Unit Tests

```bash
# Install dependencies (use a virtual environment)
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run tests with coverage report
pytest --cov=app --cov-report=xml:coverage.xml tests/
```

### Build the Docker Image

```bash
docker build \
  -t emeraldflow-app:local \
  -f Dockerfiles/app/multistage/Dockerfile .
```

### Run the Container Locally

```bash
docker run --rm \
  -p 8080:8080 \
  -e DB_HOST=localhost \
  -e DB_PASSWORD=yourpassword \
  emeraldflow-app:local
```

### Verify Health Endpoints

```bash
# Application liveness
curl -s http://localhost:8080/health | python -m json.tool

# Database connectivity check
curl -s http://localhost:8080/db-status | python -m json.tool
```

**Expected healthy response from `/health`:**

```json
{
  "status": "UP",
  "service": "emeraldflow-app",
  "runtime": "python"
}
```

---

## Repository Structure

```
emeraldflow-app/
├── .github/
│   └── workflows/
│       └── ci.yml                  # CI/CD pipeline definition
├── Dockerfiles/
│   ├── app/                        # Application container (multi-stage build)
│   ├── db/                         # Database container
│   └── web/                        # Web/proxy container (e.g. Nginx)
├── tests/                          # Pytest unit tests
├── app.py                          # Flask application entrypoint
├── requirements.txt                # Python dependencies
└── sonar-project.properties        # SonarQube scanner configuration
```

---

## Related Documentation

- [EmeraldFlow Helm Charts & Argo CD](https://github.com/Raphonkzy/emeraldflow-helm) — Kubernetes packaging and GitOps configuration
- [EmeraldFlow Infrastructure](https://github.com/Raphonkzy/emeraldflow-infra) — Terraform for AWS EKS, VPC, ECR, and IAM
- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [SonarQube Scan Action](https://github.com/SonarSource/sonarqube-scan-action)
- [Amazon ECR Login Action](https://github.com/aws-actions/amazon-ecr-login)
