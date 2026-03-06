# Know-It-All Tutor System

A serverless web application that transforms terminology-heavy subjects into interactive, ML-powered learning experiences. Users create knowledge domains, define terms, and are quizzed with semantic answer evaluation — meaning the system understands *meaning*, not just exact wording.

**Portfolio project** demonstrating production AWS architecture, multi-stack CDK IaC, CI/CD automation, and custom ML model deployment.

---

## Live Environment

| Resource | URL |
|----------|-----|
| Frontend | https://d3awlgby2429wc.cloudfront.net |
| API | https://3kuv3v3u89.execute-api.us-east-1.amazonaws.com/prod/ |
| Cognito User Pool | `us-east-1_Bg1FA4097` |

---

## Architecture

### Infrastructure: 6-Stack CDK Deployment

The system uses AWS CDK with explicit dependency ordering across six stacks:

```
NetworkStack     → VPC, subnets, security groups
DatabaseStack    → RDS PostgreSQL, Secrets Manager, DB Proxy Lambda
AuthStack        → Cognito User Pool, Pre-SignUp trigger
BackendStack     → API Gateway, Lambda functions, Lambda Layer
FrontendStack    → S3 bucket, CloudFront distribution
MonitoringStack  → CloudWatch dashboards, alarms, budget alerts
```

Each stack is independently deployable (within dependency constraints), making incremental updates fast and rollbacks surgical.

**Entry point:** `infrastructure/app_multistack.py`

### Backend: Lambda Functions

All business logic runs in Python 3.11 Lambda functions sharing a common Lambda Layer (`infrastructure/lambda_layer/python/`) that provides:
- `db_proxy_client.py` — DB Proxy pattern (all DB access goes through a proxy Lambda)
- `auth_utils.py` — Cognito JWT validation helpers
- `response_utils.py` — Standardized API response formatting

Active Lambda functions (`src/lambda_functions/`):

| Function | Purpose |
|----------|---------|
| `auth` | Login, token refresh, Cognito integration |
| `user_profile` | User account management |
| `domain_management` | CRUD for knowledge domains and terms |
| `quiz_engine` | Quiz session management and answer submission |
| `progress_tracking` | Learning progress and statistics |
| `batch_upload` | Bulk content import (JSON format) |
| `db_proxy` | Centralized database access (no direct DB connections from other Lambdas) |
| `migration_runner` | Schema migration execution |
| `db_schema_migration` | CDK custom resource for automated migrations on deploy |
| `secrets_rotation` | Automated DB credential rotation handler |
| `cognito_pre_signup` | Pre-signup validation trigger |
| `cognito_triggers` | General Cognito event handling |
| `db_migration` | Database migration utilities |

The **DB Proxy pattern** deserves mention: rather than giving every Lambda VPC access and a DB connection pool, all database calls route through a single `db_proxy` Lambda. This keeps the architecture simple and avoids connection exhaustion.

### ML: Semantic Answer Evaluation

The answer evaluator uses a custom fine-tuned DistilBERT sentence transformer, optimized to ONNX format for Lambda deployment:

- **Model:** Fine-tuned sentence-transformers model → converted to ONNX
- **Runtime:** `onnxruntime` + `transformers` (no PyTorch) → ~795MB Docker image
- **Deployment:** Docker Lambda (`lambda/answer-evaluator/`) with the model embedded
- **Result:** Semantic similarity scoring that recognizes synonyms and paraphrases — "rapid" matches "fast" matches "quick"

The ONNX conversion reduced the container size by ~60% vs PyTorch and eliminated a heavy dependency.

Local model files:
- `final_similarity_model/` — original PyTorch checkpoint (reference/retraining)
- `final_similarity_model_onnx/` — deployed ONNX version (tracked via Git LFS)

### Frontend

React 18 + TypeScript + Tailwind CSS, built with Vite.

- **Source:** `frontend/src/`
- **Build output:** `frontend/dist/` (deployed to S3 by CDK)
- **Auth:** AWS Cognito via Amplify SDK

### Database

PostgreSQL on Amazon RDS (single-instance, not Aurora Serverless — cost-optimized for a personal project).

- **Schema migrations:** versioned SQL files in `database/migrations/`, applied automatically on deploy via CDK custom resource
- **Connection pattern:** DB Proxy Lambda (see above) — no direct Lambda-to-RDS connections

---

## CI/CD

Push to `main` → GitHub Actions runs → CDK deploys (~5 minutes end-to-end).

```
.github/workflows/github-ci-cd.yml   ← active workflow
.github/workflows/rollback.yml       ← manual rollback trigger
```

Pipeline stages:
1. **Security scans** — Bandit (SAST), Checkov (IaC), TruffleHog (secrets), pip-audit (dependencies)
2. **Unit tests** — pytest with Moto (AWS mocking, no real AWS calls)
3. **CDK deploy** — `cdk deploy --all --require-approval never`
4. **Frontend build + deploy** — `npm run build` → S3 sync → CloudFront invalidation

Tests use [Moto](https://github.com/getmoto/moto) for AWS mocking rather than LocalStack — faster, no Docker required in CI, and runs in-process.

---

## Project Structure

```
infrastructure/
├── app_multistack.py           # CDK app entry point (6 stacks)
├── stacks/                     # One file per CDK stack
└── lambda_layer/python/        # Shared Lambda Layer code

src/lambda_functions/           # All Lambda business logic
lambda/answer-evaluator/        # ML inference Docker Lambda

frontend/                       # React app (Vite)
database/migrations/            # Versioned SQL migrations
tests/                          # pytest test suite
scripts/                        # Dev utilities
data/                           # Sample domain content (seed data)
docs/                           # Technical documentation

.kiro/specs/                    # System specs and design docs
.github/workflows/              # CI/CD pipelines
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- AWS CLI configured (`~/.aws/credentials`)
- AWS CDK installed (`npm install -g aws-cdk`)
- Docker (for building the answer-evaluator Lambda image)

### Local Development

```bash
# Clone and set up Python environment
git clone git@github.com:huschlej111/ai-tutor-system.git
cd ai-tutor-system
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Set up frontend
cd frontend && npm install

# Run backend tests (uses Moto — no AWS connection needed)
pytest tests/ -v --ignore=tests/test_localstack_integration.py

# Local DB setup (requires PostgreSQL running locally)
./scripts/seed-local-dev.sh
```

### Deployment

```bash
source venv/bin/activate
cd infrastructure
cdk deploy --all
```

Or just push to `main` — GitHub Actions handles it.

---

## Key Design Decisions

**Why DB Proxy Lambda instead of direct RDS access?**
VPC-attached Lambdas have cold start overhead and each needs a connection pool slot. The proxy pattern centralizes DB access, keeps non-DB Lambdas outside the VPC (faster cold starts), and prevents connection exhaustion.

**Why ONNX instead of PyTorch for the ML model?**
PyTorch adds ~1.5GB to a Lambda container. The ONNX runtime with `transformers` handles inference at ~795MB — still large, but within Lambda limits and significantly cheaper in both image storage and cold start time.

**Why 6 CDK stacks instead of one?**
Separation of concerns in deployment. Network and database changes are rare and risky — having them in separate stacks means a backend code change doesn't trigger a network stack update. It also enables faster targeted deploys (`cdk deploy BackendStack-dev`).

**Cost optimization:**
- Removed Secrets Manager VPC endpoint (~$14.40/month saved)
- RDS single-instance instead of Aurora Serverless (right-sized for dev traffic)
- ECR lifecycle policies to cap stored image count
- CloudFront caching to minimize Lambda invocations for static assets

---

## Security

See [SECURITY.md](SECURITY.md) for the full security policy.

Security scanning runs automatically in CI:
- **Bandit** — Python SAST
- **Checkov** — IaC security validation
- **TruffleHog** — secrets detection across git history
- **pip-audit** — dependency vulnerability scanning

Configuration: `.bandit`, `.checkov.yml`

---

## Testing

```bash
# Full test suite
pytest tests/ -v

# Specific modules
pytest tests/test_domain_unit.py -v
pytest tests/test_quiz_unit.py -v

# Skip integration tests that need a live DB
pytest tests/ -v --ignore=tests/integration/
```

Test breakdown:
- **Unit tests** — individual Lambda handlers with Moto mocks
- **Property-based tests** — Hypothesis for invariant testing (auth, domains, quiz, batch upload)
- **Integration tests** — full API call chains against a real local DB

---

## Specifications

Full system specs live in `.kiro/specs/`:
- `tutor-system/requirements.md` — functional requirements
- `tutor-system/design.md` — system architecture
- `tutor-system/datamodel.md` — database schema and query patterns
- `ci-cd/` — CI/CD pipeline design

---

## License

[License to be added]
