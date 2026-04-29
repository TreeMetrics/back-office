# google-docs-mcp hosting — investigation findings

For TreeMetrics/back-office#1 / TreeMetrics/google-docs-mcp#1.

## Requirement

- Users today: Alex, Enda, Garret. Workspace (`treemetrics.com`) only.
- Deliverable: stable public HTTPS URL for the MCP server (Claude Custom Connector / streamableHttp endpoint).
- Deadline: soft, ~2026-05-05.
- No SLA. Possible expansion to whole company; no timeline.
- AWS framing in the issue title was confirmed by stakeholder as a soft preference ("everything else is there"), not a hard constraint.

## PR state (TreeMetrics/google-docs-mcp#1)

In: `docker-compose.yml`, `.env.example`, `.gitignore` tweak; `docs/deploy-aws.md` (~200 lines: runtime contract, hosting comparison, OAuth setup, MCP client integration, troubleshooting). Image builds and runs locally; OAuth metadata endpoint returns expected response.

Not in: deployed service; E2E OAuth verification (blocked on Google client redirect URI + consent-screen Internal switch); host decision (marked "TBD"); persistent token store wired up; CI.

Doc gap: cold-start failure (first OAuth redirect → 404 on cold instance) is documented upstream for Cloud Run only, but applies equally to App Runner / Fargate-with-scale-to-zero. Fix is `--min-instances=1` or platform-equivalent (~$2-3/mo). Not currently mentioned in `docs/deploy-aws.md`.

## Verified infrastructure

### AWS (eu-west-1)

Prod (768576218716):
- ECS Fargate clusters: `sintetic-backend-app-production-cluster`, `fs-cluster-staging`, `geoserver-cluster-staging`
- ALBs (Fargate-targeted, app-dedicated, app-specific cert): `sintetic-be-production-alb`, `fs-service-staging-alb`, `geoserver-service-staging-alb`
- ALBs (other): `staging-hq-alb` — EC2-targeted, single target `i-0ddad08d72efc0dbf` currently unhealthy
- ECR: `sintetic-backend-app`, `forest-spatial`, `geoserver`
- ACM: `forestspatial.treemetrics.com`, `api.sintetic.treemetrics.com`, `*.sintetic.treemetrics.com`
- EC2: `treetops_backend` (t3.large), `foresthq` (m4.2xlarge), `staging_foresthq`, `beta_foresthq`

Dev (265801606451):
- 24 Lambdas (all AWSAccelerator / Control Tower platform glue)
- No ECS, App Runner, or DynamoDB
- EC2: `fw-dev`, `sintetic-dev`, three `hq-*-build`
- Route53: `preview.treemetrics.com`

Org-wide:
- IaC is CDK (CDK assets in both accounts)
- No App Runner anywhere. SCP `p-330oroph` denies `apprunner:*` in `us-west-2` and `eu-west-2`; allowed in `eu-west-1`.
- No DynamoDB tables

### Cloudflare

- `treemetrics.dev` is on Cloudflare (`cf-ray` and `server: cloudflare` in response headers).
- Named tunnel `f6425610-0852-4ce7-a8c5-97985fd350d1` routes: `forest-spatial.treemetrics.dev`, `cs-app.treemetrics.dev`, `cs-map-app.treemetrics.dev`, `cs-api.treemetrics.dev`.
- @japoveda has operated `cloudflared` for these tunnels (resolved climate-smart#129 by restarting the daemon).
- The "Cloudflare One Connector write permission" Alex was blocked on is for *his personal local-PC tunnel*. Not verified whether the same permission is needed to add new hostnames to the existing org tunnel.
- `treemetrics.com` is a separate property — WordPress on Apache, DigitalOcean (IP 67.205.2.2). Not on Cloudflare.

### GCP

Verified usage in TreeMetrics org code:
- `TreeMetrics/google-docs-mcp`: `@google-cloud/firestore` (upstream's `FirestoreTokenStorage`); reads `GCLOUD_PROJECT`. Bundled in upstream, not yet exercised against a live project.
- `TreeMetrics/ForestSpatial`: `google-cloud-storage==3.1.0` in `requirements.txt`.
- `TreeMetrics/crann-evolution`: `from google.cloud import storage` in `export_monitor.py`.
- A GCP project must exist for the Workspace OAuth client (per japoveda's PR comments referencing `gcloud run deploy`).

Not verified (no `gcloud` available locally; could not enumerate via API):
- Whether one shared GCP project or multiple.
- Whether any Cloud Run / GKE / GCE compute currently runs.
- Billing setup, IAM principals, monitoring posture.

## Hosting options

### Option 1 — App Runner (eu-west-1)
- Allowed by SCP; no other App Runner services in the org.
- `MinSize: 1` required for cold-start fix.
- Setup: ECR push, App Runner config, Secrets Manager, Cloudflare CNAME `mcp.treemetrics.dev`, OAuth redirect URI.
- Approximate effort: ~1 day. Approximate cost: ~$25-50/mo.

### Option 2 — ECS Fargate (new cluster + ALB + CDK)
- Greenfield (new cluster, ALB, ACM cert, CDK stack).
- Approximate effort: 1-2 days. Approximate cost: ~$22/mo ALB + ~$10-15/mo Fargate task.

### Option 3 — Reuse existing Fargate ALB
- The Fargate-targeted ALBs are each dedicated to one app with an app-specific cert; adding a host/path rule for MCP couples it to a production app's listener and cert.
- `staging-hq-alb` (initially considered for reuse) is EC2-targeted and currently unhealthy.

### Option 4 — Colocate on existing EC2 + Cloudflare tunnel
- `docker compose up -d` on `treetops_backend` (t3.large).
- Add `mcp.treemetrics.dev` to the existing `f6425610-…` tunnel.
- Approximate cost: $0/mo.
- Effort depends on: access to `treetops_backend`; access to the tunnel config (machine where `cloudflared` runs); noisy-neighbour assessment (what currently runs on `treetops_backend`).
- Not captured in IaC unless added.

### Option 5 — Cloud Run + Firestore
- `gcloud run deploy --source .` per upstream README.
- Firestore token store built into upstream — no adapter to write.
- `--min-instances=1` for cold-start.
- Cloudflare CNAME `mcp.treemetrics.dev`.
- Approximate cost: ~$2-3/mo.
- GCP compute usage org-wide is not verified; whether this joins an existing footprint or establishes one is unknown.

## Tradeoffs

| Axis | Option 1 | Option 2 | Option 4 | Option 5 |
|------|---|---|---|---|
| Setup effort | ~1 day | 1-2 days | Depends on coordination | Single command per upstream README |
| Approx. $/mo | $25-50 | $32-37 | $0 | $2-3 |
| Token persistence | In-memory or new DDB adapter (~100 LOC) | Same | Same | Firestore (already in upstream) |
| In IaC | CDK | CDK | Not by default | Not by default |
| Platform already used in-org | AWS (yes) | AWS (yes) | EC2 + Cloudflare tunnel pattern (climate-smart) | GCS used in 2 repos; compute not verified |

## PR-level edits to TreeMetrics/google-docs-mcp#1

- Add cold-start / `--min-instances=1` (or platform-equivalent) note to `docs/deploy-aws.md`.
- Replace the `aws apprunner` CLI deploy sketch with the chosen option's path.
- Drop the "AWS service: TBD" framing once an option is chosen.
- Rename `docs/deploy-aws.md` if the chosen option isn't AWS.

## Pre-deploy work (regardless of option)

- Google OAuth client: Web application type.
- Authorised redirect URI: `${BASE_URL}/oauth/callback` per environment.
- Consent screen: Internal (Workspace-only, no verification review).
- Enable APIs on the GCP project: Docs, Sheets, Drive, Gmail, Calendar, Apps Script.
- Authorise the full scope list on the consent screen.
- `ALLOWED_DOMAINS=treemetrics.com` (defence-in-depth).
- Pin `JWT_SIGNING_KEY` so issued MCP tokens survive restarts.
