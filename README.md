# Know-It-All Tutor System

A serverless web application that transforms terminology-heavy subjects into interactive, ML-powered learning experiences. Users create knowledge domains, define terms, and are quizzed with semantic answer evaluation — meaning the system understands *meaning*, not just exact wording.

**Portfolio project** demonstrating production AWS architecture, multi-stack CDK IaC, CI/CD automation, and custom ML model deployment.

---

## Try It

The application is live at [https://d3awlgby2429wc.cloudfront.net/](https://d3awlgby2429wc.cloudfront.net/).

If you'd like to explore it, you can register for an account at the link above. Accounts aren't provisioned automatically — registration lands in a review queue and access is granted manually.

Why the gate? Two reasons, both honest: bots are a real nuisance, and the free-tier cost model described below depends on keeping traffic predictable. Automated signups solve neither problem and create new ones. So a human reviews each request. If you're a real person who wants to poke around, you'll hear back.

---

## Engineering for Zero Fixed Costs, or Jim is sooo cheap

A deliberate constraint shaped this project's architecture: every component with a fixed monthly charge was either eliminated or replaced with a pay-per-use equivalent. At low traffic the effective AWS bill is pennies per month. That produced several tradeoffs that don't appear in standard architecture guides.

**ML model: CPU inference within ECR's free storage ceiling**
Lambda runs on CPU only, and ECR's always-free tier covers 500 MB/month of private image storage. The answer evaluator started as a PyTorch sentence-transformers model (container well over 1 GB) and was progressively compressed:
- Replaced PyTorch + `transformers` with `onnxruntime` + `tokenizers` (no PyTorch at runtime)
- Applied int8 quantization to the cross-encoder weights
- Final image: ~112 MB — well under ECR's 500 MB always-free ceiling and Lambda's 10 GB cap

Cross-encoders are slower than bi-encoders, but each quiz answer requires only a single pair comparison (not retrieval over a corpus), so CPU latency is acceptable.

**Networking: staying off the VPC cost surface**
VPC Interface Endpoints, NAT gateways, and cross-AZ data transfer all carry charges. Two decisions keep the network bill near zero:
- Only `db_proxy` sits inside the VPC with database access. Every other Lambda invokes it by name over the Lambda control plane — no VPC attachment, no NAT gateway required.
- VPC Interface Endpoints were removed. At this traffic level, the cost (~$14.40/month per endpoint) isn't justified.

**Database: replacing RDS's fixed cost with DSQL's free tier**
RDS PostgreSQL (`t4g.micro`) has no always-free tier and costs roughly $15–18/month regardless of traffic. Aurora DSQL includes a permanent free tier — 100,000 DPUs and 1 GB of storage per month — which comfortably covers a low-traffic application like this one.

The migration required removing every feature DSQL doesn't support: foreign key constraints, triggers, PL/pgSQL functions, sequences, and synchronous DDL. Application code now enforces referential integrity, the migration runner issues one DDL statement per transaction with `CREATE INDEX ASYNC`, and the DB proxy layer adds OCC retry logic for the optimistic concurrency model.

**Storage: keeping S3 to static assets**
S3 has no always-free storage tier — after the 12-month introductory period, storage and per-request charges accumulate with usage. To keep this surface small:
- Generated domain content and quiz data live in DSQL rather than S3; every quiz-question load avoids a per-object GET charge.
- The ML model is baked into the Lambda container image rather than fetched from S3 at cold start, trading a one-time ECR storage cost for zero per-invocation object reads.
- CloudFront caching keeps origin fetches to the S3 frontend bucket low, minimizing both data transfer and GET request counts.

That is pinching your development pennies until they scream.  

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
- **Runtime:** `onnxruntime` + `tokenizers` (no PyTorch, no `transformers`) → ~112MB Docker image
- **Deployment:** Docker Lambda (`lambda/answer-evaluator/`) with the model baked in
- **Scoring:** sigmoid(logit) → min-max normalized over an empirical calibration range; pass threshold 0.50
- **Result:** Semantic similarity scoring that recognizes synonyms and paraphrases — "rapid" matches "fast" matches "quick". Supports single-pair and batch evaluation.

Dropping PyTorch and `transformers` kept the container well under the 10 GB Lambda image limit and cut cold-start time significantly.

### Content Pipeline: Domain Generation

Quiz content — knowledge domains, subdomains, and term definitions — is generated by a local LLM pipeline rather than hand-authored or purchased. The pipeline runs against a self-hosted vLLM instance on the LAN and uses a two-prompt architecture:

**Prompt 1 — decomposition:** Given a topic, a curriculum-architect prompt instructs the model to decompose it into 4–7 coherent subdomains ordered from foundational to advanced, with authoritative sources and targeted search queries for each. The prompt enforces strict JSON output and explicit rules about source specificity — linking to the most relevant subsection of documentation rather than a chapter index.

**Prompt 2 — term emission:** For each subdomain, a tool-calling agent searches the web, scrapes authoritative sources, and emits terms one at a time via a structured `emit_term` tool. Each term includes a full definition, a `short_reference` (1–2 sentence answer used as the model's comparison target during quiz evaluation), difficulty rating, and related terms. The agent loop runs up to 25 turns with a sliding context window to avoid OOM on the local GPU.

The prompts are in `pipeline/domain_gen/prompts.py`. Iteration history and per-language cleanup rules are in `pipeline/`.

**The overnight kludge:** Running LLM inference on cloud infrastructure would cost real money and remember how cheap I am. Instead, the pipeline runs as a nightly cron job on the LAN machine, picking up jobs queued by any authenticated user via the domain generation UI and processing them overnight. This is the same architectural philosophy as the DSQL free tier and the ECR container size budget — trade engineering complexity and operational constraints for a zero cost line item. The tradeoff is that domain generation is slow (hours per topic) and depends on the LAN machine being up.

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

The project supports two parallel, fully automated CI/CD pipelines that handle the entire build, test, and deploy lifecycle:

* **GitHub Actions** (`.github/workflows/github-ci-cd.yml`) — Runs on push/PR to `main` and manually via `workflow_dispatch`.
* **Gitea Actions** (`.gitea/workflows/gitea-ci.yml`) — Runs on push/PR to `main` and `develop` on the local Gitea instance.

### Pipeline Stages
1. **Security Scans:** Runs Bandit (SAST), Checkov (IaC), TruffleHog (secrets detection), and pip-audit (dependencies).
2. **Backend Unit Tests:** Runs `pytest` in a test environment with a local PostgreSQL service container, mocking AWS calls using Moto.
3. **Frontend Build:** Builds the React application with production environment parameters.
4. **AWS CDK Deployment:** Deploys all 6 stacks sequentially (`AuthStack-dev`, `BackendStack-dev`, `DatabaseStack-dev`, `FrontendStack-dev`, `MonitoringStack-dev`, and `NetworkStack-dev`) to avoid CloudFormation dependency blockages.
5. **Post-Deployment Tasks:** Triggers database migrations via AWS Lambda invocation, invalidates the CloudFront CDN cache, and sets up ECR container lifecycle policies.

### Required GitHub Secrets
To enable deployment from the GitHub Actions pipeline, you must configure the following repository secrets under `Settings -> Secrets and variables -> Actions`:
* `AWS_ACCESS_KEY_ID` & `AWS_SECRET_ACCESS_KEY` — AWS IAM credentials for deployment.
* `VITE_API_BASE_URL` — The base URL of the deployed API Gateway.
* `VITE_COGNITO_USER_POOL_ID` & `VITE_COGNITO_USER_POOL_CLIENT_ID` — Cognito authentication settings.

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
PyTorch adds ~1.5GB to a Lambda container. Using `onnxruntime` + `tokenizers` (no `transformers`) keeps the image at ~112MB — well under Lambda's 10 GB limit and meaningfully cheaper in both ECR storage and cold-start time.

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
