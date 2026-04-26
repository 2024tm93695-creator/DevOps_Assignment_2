# ACEest Fitness & Gym — CI/CD Pipeline

A Python Flask REST API for fitness and gym client management, built with a fully automated CI/CD pipeline using Jenkins, Docker, SonarQube, and Kubernetes.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Application API](#application-api)
- [Getting Started](#getting-started)
- [Running Tests](#running-tests)
- [Docker](#docker)
- [CI/CD Pipeline](#cicd-pipeline)
- [Kubernetes Deployment Strategies](#kubernetes-deployment-strategies)
- [SonarQube Code Quality](#sonarqube-code-quality)

---

## Project Overview

**ACEest Fitness & Gym** (v3.2.4) is a Flask REST API that manages gym clients, workout logs, body metrics, progress tracking, and BMI calculations. The project demonstrates a production-grade DevOps pipeline with four Kubernetes deployment strategies: rolling update, blue-green, canary, and shadow.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Application | Python 3.12, Flask 3.0.3 |
| Database | SQLite (embedded) |
| Testing | pytest, pytest-cov |
| Code Quality | SonarQube / SonarCloud |
| CI/CD | Jenkins (declarative pipeline) |
| Containerisation | Docker (multi-stage build) |
| Container Registry | Docker Hub (`098765421/aceest-fitness`) |
| Orchestration | Kubernetes / Minikube |
| Local Infrastructure | Docker Compose |

---

## Project Structure

```
.
├── app.py                          # Flask application
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Multi-stage Docker build
├── docker-compose.yml              # Local app + SonarQube + PostgreSQL
├── Jenkinsfile                     # CI/CD pipeline definition
├── sonar-project.properties        # SonarCloud configuration
├── pytest.ini                      # Test runner configuration
├── setup.cfg                       # Project metadata
├── tests/
│   └── test_app.py                 # Full pytest test suite
├── k8s/
│   ├── namespace.yaml              # aceest namespace
│   ├── deployment.yaml             # Rolling update deployment
│   ├── service.yaml                # LoadBalancer service
│   ├── blue-green/
│   │   ├── blue-deployment.yaml    # Stable version (v3.1.2)
│   │   ├── green-deployment.yaml   # New version (v3.2.4)
│   │   └── service.yaml            # Switchable service selector
│   ├── canary/
│   │   ├── stable-deployment.yaml
│   │   ├── canary-deployment.yaml
│   │   └── service.yaml
│   ├── shadow/
│   │   ├── primary-deployment.yaml
│   │   └── shadow-deployment.yaml
│   └── ab-testing/
│       ├── variant-a-deployment.yaml
│       ├── variant-b-deployment.yaml
│       └── ingress.yaml
└── reports/                        # Generated test and coverage reports
```

---

## Application API

Base URL: `http://localhost:5000`

### Health & Info

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | App info and endpoint list |
| GET | `/health` | Health check — returns `{"status": "healthy"}` |
| GET | `/programs` | List available fitness programs |

### Client Management

| Method | Endpoint | Description |
|---|---|---|
| POST | `/clients` | Create a new client |
| GET | `/clients` | List all clients |
| GET | `/clients/<name>` | Get a specific client |
| PUT | `/clients/<name>` | Update client details |
| DELETE | `/clients/<name>` | Delete a client |

### Tracking

| Method | Endpoint | Description |
|---|---|---|
| POST | `/clients/<name>/progress` | Log weekly adherence (0–100) |
| GET | `/clients/<name>/progress` | Get progress history |
| POST | `/clients/<name>/workouts` | Log a workout session |
| GET | `/clients/<name>/workouts` | Get workout history |
| POST | `/clients/<name>/metrics` | Log body metrics (weight, waist, body fat) |
| GET | `/clients/<name>/metrics` | Get metrics history |
| GET | `/clients/<name>/bmi` | Calculate BMI |

### Available Fitness Programs

| Program | Calorie Factor |
|---|---|
| Fat Loss (FL) - 3 day | 22 × body weight (kg) |
| Fat Loss (FL) - 5 day | 24 × body weight (kg) |
| Muscle Gain (MG) - PPL | 35 × body weight (kg) |
| Beginner (BG) | 26 × body weight (kg) |

### Example Request

```bash
# Create a client
curl -X POST http://localhost:5000/clients \
  -H "Content-Type: application/json" \
  -d '{"name": "Arjun Kumar", "age": 28, "height": 175, "weight": 78, "program": "Fat Loss (FL) - 3 day"}'

# Log a workout
curl -X POST http://localhost:5000/clients/Arjun%20Kumar/workouts \
  -H "Content-Type: application/json" \
  -d '{"workout_type": "Strength", "duration_min": 60, "exercises": [{"name": "Squat", "sets": 5, "reps": 5, "weight": 100}]}'
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- Docker Desktop
- Minikube
- kubectl
- Jenkins (with Docker and kubectl access)

### Run Locally

```bash
# 1. Clone the repository
git clone <repo-url>
cd Devops_Assignment_2

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start the app
python app.py
# API available at http://localhost:5000
```

### Run with Docker Compose (includes SonarQube)

```bash
docker compose up -d

# Services:
#   App        → http://localhost:5000
#   SonarQube  → http://localhost:9000  (admin/admin)
```

---

## Running Tests

```bash
# Activate virtual environment first
source venv/bin/activate

# Run all tests with coverage
pytest tests/ \
  --junitxml=reports/junit.xml \
  --cov=app \
  --cov-report=xml:reports/coverage.xml \
  --cov-report=html:reports/htmlcov \
  -v
```

Coverage report is generated at `reports/htmlcov/index.html`.

**Test classes:**

| Class | What it covers |
|---|---|
| `TestCalculateBMI` | BMI calculation logic and edge cases |
| `TestCalculateCalories` | Calorie calculation per program |
| `TestInfoEndpoints` | Health, index, programs routes |
| `TestClientCRUD` | Create, read, update, delete clients |
| `TestProgress` | Weekly adherence logging |
| `TestWorkouts` | Workout and exercise logging |
| `TestMetrics` | Body metrics tracking |
| `TestBMIEndpoint` | BMI REST endpoint |

---

## Docker

### Build and Run

```bash
# Build
docker build -t 098765421/aceest-fitness:3.2.4 .

# Run
docker run -p 5000:5000 098765421/aceest-fitness:3.2.4

# Push to Docker Hub
docker push 098765421/aceest-fitness:3.2.4
docker push 098765421/aceest-fitness:latest
```

### Image Design

The Dockerfile uses a **two-stage build**:
- **Stage 1 (builder):** Installs dependencies — build tools stay out of the final image
- **Stage 2 (runtime):** Copies only the app and installed packages into `python:3.12-slim`
- Runs as non-root user `aceest`
- Health check polls `/health` every 30 seconds

---

## CI/CD Pipeline

The `Jenkinsfile` defines a declarative pipeline triggered on every `git push`.

### Pipeline Flow

```
Checkout → Install Deps → Unit Tests → SonarQube → Quality Gate
    → Build Image → Push Image → Deploy → Smoke Test
```

### Branch-Based Deployment Routing

| Branch | Deployment Strategy |
|---|---|
| `main` | Rolling update + smoke test |
| `release/*` | Canary deployment (10% traffic) |

### Jenkins Credentials Required

| Credential ID | Type | Used For |
|---|---|---|
| `dockerhub-credentials` | Username/Password | Docker Hub push |
| `sonarcloud-token` | Secret text | SonarCloud analysis |
| `kubeconfig` | Secret file | kubectl access |

### Pipeline Options

- Keeps last 10 builds (`logRotator`)
- 30-minute timeout per build
- Timestamps on all log output
- Workspace cleaned after every build

---

## Kubernetes Deployment Strategies

### Prerequisites

```bash
# Start Minikube
minikube start --driver=docker --cpus=2 --memory=4096 --kubernetes-version=v1.28.3

# Create namespace
kubectl apply -f k8s/namespace.yaml
```

### 1. Rolling Update (default — main branch)

```bash
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl rollout status deployment/aceest-fitness -n aceest

# Update image
kubectl set image deployment/aceest-fitness aceest-fitness=098765421/aceest-fitness:latest -n aceest

# Rollback
kubectl rollout undo deployment/aceest-fitness -n aceest
```

### 2. Blue-Green Deployment

```bash
kubectl apply -f k8s/blue-green/blue-deployment.yaml
kubectl apply -f k8s/blue-green/green-deployment.yaml
kubectl apply -f k8s/blue-green/service.yaml

# Switch traffic to green (PowerShell)
kubectl patch service aceest-fitness-svc -n aceest -p '{\"spec\":{\"selector\":{\"slot\":\"green\"}}}'

# Rollback to blue
kubectl patch service aceest-fitness-svc -n aceest -p '{\"spec\":{\"selector\":{\"slot\":\"blue\"}}}'
```

| Slot | Version | Image |
|---|---|---|
| blue | v3.1.2 | `098765421/aceest-fitness:3.1.2` |
| green | v3.2.4 | `098765421/aceest-fitness:3.2.4` |

### 3. Canary Deployment

```bash
kubectl apply -f k8s/canary/stable-deployment.yaml
kubectl apply -f k8s/canary/canary-deployment.yaml
kubectl apply -f k8s/canary/service.yaml

# Check pods (stable vs canary)
kubectl get pods -n aceest -L track
```

### 4. Shadow Deployment

```bash
kubectl apply -f k8s/shadow/primary-deployment.yaml
kubectl apply -f k8s/shadow/shadow-deployment.yaml

# Check pods by role
kubectl get pods -n aceest -L role

# Rollback: delete shadow
kubectl delete deployment aceest-fitness-shadow -n aceest
```

### Verify Deployments

```bash
kubectl get deployments -n aceest
kubectl get pods -n aceest
kubectl get svc -n aceest

# Access the app
minikube service aceest-fitness-svc -n aceest
```

---

## SonarQube Code Quality

### Via Docker Compose (local)

```bash
docker compose up -d sonarqube sonar-db
# Wait ~60 seconds for startup
# Open http://localhost:9000  (admin / admin)
```

### Run Analysis

```bash
sonar-scanner \
  -Dsonar.host.url=http://localhost:9000 \
  -Dsonar.token=<your-token>
```

### Configuration (`sonar-project.properties`)

| Property | Value |
|---|---|
| Project Key | `aceest-fitness` |
| Organisation | `prasannamanne` |
| Sources | `app.py` |
| Tests | `tests/` |
| Coverage report | `reports/coverage.xml` |
| Test report | `reports/junit.xml` |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PORT` | `5000` | Port the Flask app listens on |
| `FLASK_DEBUG` | `false` | Enable Flask debug mode |
| `APP_VERSION` | `3.2.4` | Reported in `/health` and `/` responses |
| `DB_NAME` | `aceest_fitness.db` | SQLite database file path |
