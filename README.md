# Cloud Platform — Internal Developer Portal

Self-hosted developer platform for service catalog management, self-service infrastructure provisioning (Terraform), environment lifecycle, cost tracking, and AI-powered infrastructure advice via AWS Bedrock.

```
                        ┌──────────────────────────────────┐
                        │          Dashboard (SPA)         │
                        │   Tailwind CSS · fetch() API     │
                        └──────────────┬───────────────────┘
                                       │
                        ┌──────────────▼───────────────────┐
                        │         FastAPI Server           │
                        │  /api/services  /api/environments│
                        │  /api/ai/suggest   /api/costs    │
                        └───┬──────────┬──────────┬────────┘
                            │          │          │
                  ┌─────────▼──┐  ┌────▼────┐  ┌──▼──────────┐
                  │  SQLite DB │  │Terraform│  │AWS Bedrock  │
                  │  services  │  │  CLI    │  │Claude Haiku │
                  │  envs      │  │  plan   │  │suggestions  │
                  └────────────┘  │  apply  │  └─────────────┘
                                  │  destroy│
                                  └────┬────┘
                                       │
                              ┌────────▼────────┐
                              │   AWS Account   │
                              │ ECS / Lambda    │
                              │ VPC / ALB / IAM │
                              │ CloudWatch      │
                              │ Cost Explorer   │
                              └─────────────────┘
```

## Features

- **Service Catalog** — Register and track microservices (web, API, worker)
- **Self-Service Provisioning** — Create dev/staging/prod environments with one click; Terraform runs under the hood
- **Environment Management** — View status, destroy environments, track lifecycle
- **AI Advisor** — Ask AWS Bedrock (Claude) for infrastructure recommendations, Terraform code generation, and cost explanations
- **Cost Tracking** — Per-service cost breakdown via AWS Cost Explorer
- **Dark-Themed Dashboard** — Single-page HTML app, no build step required

## Quick Start

```bash
# Clone and install
git clone <repo-url> && cd cloud-platform
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# Configure
cp .env.example .env
# Edit .env with your AWS credentials

# Run
make dev
# Open http://localhost:8000
```

## API Reference

| Method   | Endpoint                 | Description                       |
|----------|--------------------------|-----------------------------------|
| `GET`    | `/health`                | Health check                      |
| `POST`   | `/api/services`          | Register a service                |
| `GET`    | `/api/services`          | List all services                 |
| `GET`    | `/api/services/{id}`     | Get service details               |
| `POST`   | `/api/environments`      | Create environment (triggers TF)  |
| `GET`    | `/api/environments`      | List environments                 |
| `DELETE` | `/api/environments/{id}` | Destroy environment               |
| `POST`   | `/api/ai/suggest`        | AI infrastructure recommendations |
| `GET`    | `/api/costs`             | Cost summary per service          |

### Example: Register a service

```bash
curl -X POST http://localhost:8000/api/services \
  -H "Content-Type: application/json" \
  -d '{"name": "payment-api", "type": "api", "owner": "platform-team", "repo_url": "https://github.com/org/payment-api"}'
```

### Example: Create an environment

```bash
curl -X POST http://localhost:8000/api/environments \
  -H "Content-Type: application/json" \
  -d '{"service_id": 1, "name": "dev", "region": "us-east-1"}'
```

### Example: Ask AI advisor

```bash
curl -X POST http://localhost:8000/api/ai/suggest \
  -H "Content-Type: application/json" \
  -d '{"prompt": "I need a web service handling 5000 requests/sec with a PostgreSQL database"}'
```

## Project Structure

```
cloud-platform/
├── src/
│   ├── api/
│   │   ├── main.py          # FastAPI application
│   │   ├── models.py        # Pydantic models
│   │   └── database.py      # SQLite helper
│   ├── ai/
│   │   └── advisor.py       # AWS Bedrock integration
│   ├── provisioner/
│   │   └── terraform.py     # Terraform CLI wrapper
│   └── dashboard/
│       └── index.html        # SPA dashboard
├── terraform/
│   ├── provider.tf
│   └── modules/
│       ├── service/          # ECS/Lambda + ALB + IAM
│       └── environment/      # VPC + subnets + SGs
├── tests/
│   └── test_api.py
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── requirements.txt
```

## Development

```bash
make install-dev   # Install all dependencies
make test          # Run pytest
make lint          # Run ruff
make format        # Auto-format code
make dev           # Start dev server with hot reload
make docker-build  # Build container image
make docker-run    # Start with docker compose
```

## Prerequisites

- Python 3.11+
- Terraform >= 1.5 (for provisioning)
- AWS account with Bedrock access (for AI features)
- Docker (optional, for containerized deployment)

## License

MIT
