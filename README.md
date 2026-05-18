# Know-It-All Tutor System

A serverless web application that transforms terminology-heavy subjects into interactive, ML-powered learning experiences. Users create knowledge domains, define terms, and are quizzed with semantic answer evaluation — meaning the system understands *meaning*, not just exact wording.

**Portfolio project** demonstrating production AWS architecture, multi-stack CDK IaC, CI/CD automation, and custom ML model deployment.

---

## Live Environment

| Resource | URL |
|----------|-----|
| Frontend | https://d3awlgby2429wc.cloudfront.net |

API endpoint and Cognito configuration are available from CloudFormation outputs after deployment.

---

## Architecture

### Infrastructure: 6-Stack CDK Deployment

The system uses AWS CDK with explicit dependency ordering across six stacks:

```
NetworkStack     → VPC, subnets, security groups
DatabaseStack    → RDS PostgreSQL, Secrets Manager, DB Proxy Lambda
AuthStack        → Cognito User Pool, Pre-SignUp trigger, custom approval attributes
BackendStack     → API Gateway, Lambda functions, Lambda Layer
FrontendStack    → S3 bucket, CloudFront distribution
MonitoringStack  → CloudWatch dashboards, alarms, budget alerts
```

Each stack is independently deployable (within dependency constraints), making incremental updates fast and rollbacks surgical.

**Entry point:** `infrastructure/app_multistack.py`

### Backend: Lambda Functions

All business logic runs in Python 3.11 Lambda functions sharing a common Lambda Layer (`infrastructure/lambda_layer/python/`). See the shared module table below.

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
| `cognito_pre_signup` | Pre-signup trigger: validates registration and stamps pending-approval status |
| `cognito_triggers` | Cognito event handlers including Pre-Authentication trigger that enforces the approval gate |
| `user_management` | Admin review queue: list pending registrations, approve or deny with email notification |
| `db_migration` | Database migration utilities |

The **DB Proxy pattern** deserves mention: rather than giving every Lambda VPC access and a DB connection pool, all database calls route through a single `db_proxy` Lambda. This keeps the architecture simple and avoids connection exhaustion.

### Registration & Approval Gate

New user registrations are held in a pending state rather than granted immediate access. The flow:

1. User registers → Pre-SignUp Lambda stamps a custom `approval_status` attribute on the Cognito user record.
2. The account exists but cannot log in — a Pre-Authentication Lambda trigger checks the attribute and rejects unapproved users at login time.
3. An admin reviews pending registrations via the admin API and approves or denies each one.
4. Approval updates the Cognito attribute and sends an email notification via SES.

Admin API routes (Cognito-authorized; admin group membership enforced inside the Lambda):

| Method | Route | Purpose |
|--------|-------|---------|
| `GET` | `/admin/users/pending` | List users awaiting approval |
| `POST` | `/admin/users/{username}/approve` | Approve a pending user |
| `POST` | `/admin/users/{username}/deny` | Deny and remove a pending user |

The Lambda Layer (`infrastructure/lambda_layer/python/`) provides shared code to all functions:

| Module | Purpose |
|--------|---------|
| `db_proxy_client.py` | DB Proxy invocation client |
| `auth_utils.py` | Cognito JWT validation |
| `authorization_utils.py` | Route-level authorization enforcement |
| `response_utils.py` | Standardized API response formatting |
| `security_middleware.py` | Input sanitization and rate-limit headers |
| `security_monitoring.py` | Security event logging |
| `secrets_client.py` | Secrets Manager access |
| `config.py` | Environment-aware configuration |
| `database.py` | Connection helpers (used by db_proxy) |

### ML: Semantic Answer Evaluation

The answer evaluator uses a cross-encoder model fine-tuned from NLI → STSB, exported to int8-quantized ONNX for Lambda deployment:

- **Model:** Cross-encoder (NLI pre-trained → STSB fine-tuned), int8 quantized ONNX (~79 MB)
- **Runtime:** `onnxruntime` + `tokenizers` (no PyTorch, no `transformers`) → ~456MB Docker image
- **Deployment:** Docker Lambda (`lambda/answer-evaluator/`) with the model baked in
- **Scoring:** sigmoid(logit) → min-max normalized over an empirical calibration range; pass threshold 0.50
- **Result:** Semantic similarity scoring that recognizes synonyms and paraphrases — "rapid" matches "fast" matches "quick". Supports single-pair and batch evaluation.

Dropping PyTorch and `transformers` kept the container well under the 10 GB Lambda image limit and cut cold-start time significantly.

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

```
.github/workflows/github-ci-cd.yml   ← security scans + unit tests (on push/PR)
.github/workflows/rollback.yml       ← manual rollback trigger
```

GitHub Actions pipeline stages (runs on every push to `main` and on PRs):
1. **Security scans** — Bandit (SAST), Checkov (IaC), TruffleHog (secrets), pip-audit (dependencies)
2. **Unit tests** — pytest with Moto (AWS mocking, no real AWS calls)

CDK deployment is triggered separately via a self-hosted Gitea CI pipeline, which handles:
- `cdk deploy --all --require-approval never`
- `npm run build` → S3 sync → CloudFront invalidation

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
```

#### Running the full stack locally (SAM)

AWS SAM runs the API Gateway and Lambda functions in Docker containers on your machine.
The frontend dev server (Vite) talks to the local API instead of production.

**One-time setup:**

```bash
# 1. Install SAM CLI (https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)

# 2. Create the local test database (requires PostgreSQL running)
sudo -u postgres psql -f scripts/sql/setup-ci-testdb.sql

# 3. Apply schema + migrations
psql postgresql://testuser:testpassword@localhost/tutor_system_test \
     -f database/migrations/schema_v2.sql
psql postgresql://testuser:testpassword@localhost/tutor_system_test \
     -f database/migrations/003_add_public_domains.sql
psql postgresql://testuser:testpassword@localhost/tutor_system_test \
     -f database/migrations/004_update_quiz_sessions_schema.sql

# 4. Seed your Cognito user into the local DB (fetches your sub from AWS automatically)
./scripts/seed-local-dev.sh

# 5. Pre-pull the Lambda Docker image (optional, saves time on first run)
docker pull public.ecr.aws/lambda/python:3.12
```

**Daily use:**

```bash
./dev.sh
# Opens:
#   http://localhost:5173  — frontend (Vite)
#   http://localhost:3000  — API (SAM)
# Ctrl-C stops everything.
```

`dev.sh` starts three processes: a TCP proxy that bridges Docker containers to
host PostgreSQL (port 15432 → 5432), the SAM local API gateway, and the Vite
dev server. First request to each endpoint has a ~10s cold start.

The `template.yaml` at the project root mirrors the CDK backend stack routes.
`LOCAL_DEV=true` activates shims in the Lambda Layer so that:
- `auth_utils.py` decodes Cognito JWTs from the Authorization header directly
  (SAM doesn't run the Cognito authorizer)
- `db_proxy_client.py` queries PostgreSQL directly instead of invoking the DB
  Proxy Lambda
- `response_utils.py` sets CORS to `http://localhost:5173`

> **Note:** The ML answer evaluator (`POST /quiz/evaluate`) is omitted from the
> local template — it requires a ~456MB Docker image. The rest of the quiz flow
> (start, question, answer) works without it.

#### Running tests only

```bash
# Run backend tests (uses Moto — no AWS connection needed)
pytest tests/ -v --ignore=tests/test_localstack_integration.py
```

### Deployment

```bash
source venv/bin/activate
cdk deploy --all
```

---

## Key Design Decisions

**Why DB Proxy Lambda instead of direct RDS access?**
VPC-attached Lambdas have cold start overhead and each needs a connection pool slot. The proxy pattern centralizes DB access, keeps non-DB Lambdas outside the VPC (faster cold starts), and prevents connection exhaustion.

**Why ONNX instead of PyTorch for the ML model?**
PyTorch adds ~1.5GB to a Lambda container. Using `onnxruntime` + `tokenizers` (no `transformers`) keeps the image at ~456MB — well under Lambda's 10 GB limit and meaningfully cheaper in both ECR storage and cold-start time.

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
- `quiz-engine-deployment/` — ML inference deployment design
- `student-teacher/` — multi-role user model design

---

## License

[License to be added]
