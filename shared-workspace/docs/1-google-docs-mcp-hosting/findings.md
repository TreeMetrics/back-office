# google-docs-mcp hosting — investigation findings

Investigation of TreeMetrics/back-office#1 / TreeMetrics/google-docs-mcp#1.

Revisions:
- v1: initial review of japoveda's PR.
- v2: amended after independent review of reviewer claims (caught the App Runner / Fargate / EC2-targeted-ALB confusion).
- v3 *(this doc)*: stakeholder questions answered. Cloudflare estate verified — `treemetrics.dev` is the Cloudflare zone, not `treemetrics.com`. Recommendation sharpened to Option 4.

## Requirement (signal vs noise)

- **Users**: Alex, Enda, Garret. Currently only Alex actively using it. Internal Workspace (`treemetrics.com`) only.
- **Deliverable**: a stable public HTTPS URL for the MCP server so coworkers can add it as a Custom Connector / streamableHttp endpoint.
- **Deadline**: soft, ~2026-05-05. Alex framed it as nice-to-have: *"if it is not much time or too complicated… otherwise we will also manage."*
- **No SLA, no PII risk beyond what Workspace already permits**, ~3 users today, possibly company-wide later (no timeline).
- **AWS framing**: confirmed as a soft preference ("where everything else is"), not a hard constraint. See "Stakeholder answers" below.

## PR state (TreeMetrics/google-docs-mcp#1)

What's in the PR:
- `docker-compose.yml` (host 8088 → container 8080), `.env.example`, `.gitignore` tweak
- `docs/deploy-aws.md` — 200 lines: runtime contract, hosting comparison (App Runner / ECS Fargate / EC2), OAuth / consent-screen guide, MCP client onboarding, troubleshooting
- Image builds, container runs locally, OAuth metadata endpoint verified

What's not in the PR:
- No service deployed
- E2E OAuth flow not verified (blocked on adding redirect URI to Google client + GCP consent-screen Internal switch)
- AWS service choice "TBD"
- No token-persistence adapter (in-memory only)
- No CI

Doc gap (caught in review): the cold-start failure mode (first OAuth redirect → Claude 404 page) is documented in upstream README for Cloud Run and applies equally to App Runner / Fargate-with-scale-to-zero. Fix is `--min-instances=1` (~$2-3/mo). Not mentioned in `deploy-aws.md`. Should be added before merge regardless of host choice.

## AWS estate (verified)

Region: **eu-west-1** for everything.

**Prod account (768576218716):**
- ECS Fargate clusters: `sintetic-backend-app-production-cluster`, `fs-cluster-staging`, `geoserver-cluster-staging`
- ALBs:
  - `sintetic-be-production-alb` — target type `ip` (Fargate), serves sintetic
  - `fs-service-staging-alb` — target type `ip` (Fargate), serves forest-spatial staging
  - `geoserver-service-staging-alb` — target type `ip` (Fargate), serves geoserver staging
  - `staging-hq-alb` — target type **`instance`** (EC2), single target `i-0ddad08d72efc0dbf` currently `unhealthy`, cert is `forestspatial.treemetrics.com`
- ECR repos: `sintetic-backend-app`, `forest-spatial`, `geoserver`, plus CDK assets
- ACM certs: `forestspatial.treemetrics.com`, `api.sintetic.treemetrics.com`, `*.sintetic.treemetrics.com`
- EC2 instances (running): `treetops_backend` (t3.large), `foresthq` (m4.2xlarge), `staging_foresthq`, `beta_foresthq`

**Dev account (265801606451):**
- 24 Lambdas — all AWSAccelerator / Control Tower platform glue, not application code
- No ECS, no App Runner, no DynamoDB
- EC2 running: `fw-dev`, `sintetic-dev`, three `hq-*-build` boxes
- Route53: `preview.treemetrics.com` only

**Org-wide:**
- CDK is the IaC (CDK accel ECR repos in both accounts)
- No App Runner anywhere; SCP `p-330oroph` denies `apprunner:*` in `us-west-2` and `eu-west-2` — allowed in `eu-west-1`. Signals an org-level opinion has already been taken.
- No DynamoDB tables

## Cloudflare estate (verified, corrects earlier note)

- `treemetrics.com` is **not** on Cloudflare — it's WordPress on Apache (DigitalOcean, IP 67.205.2.2). Earlier note was wrong.
- `treemetrics.dev` **is** the org's Cloudflare zone, used as the public surface for tunneled internal tools (`cf-ray` confirmed in headers).
- A named tunnel already exists: UUID `f6425610-0852-4ce7-a8c5-97985fd350d1`, with active hostnames `forest-spatial.treemetrics.dev`, `cs-app.treemetrics.dev`, `cs-map-app.treemetrics.dev`, `cs-api.treemetrics.dev` (climate-smart team).
- **japoveda already operates `cloudflared`** (resolved climate-smart#129 by restarting it).
- The "Cloudflare One Connector write permission" Alex is blocked on is for **his personal local-PC tunnel**. Adding `mcp.treemetrics.dev` to the existing org tunnel does **not** require it.
- Net effect: a "Cloudflare tunnel + `treemetrics.dev` + `cloudflared` on a server" pattern is already in production for internal tools. This is *the* internal-tools pattern, not an alternative to one.

## Options

### Option 1 — App Runner (eu-west-1)

- New surface for the org (no existing App Runner services), but allowed by SCP in this region
- Built-in HTTPS, autoscale, deploy-from-ECR, secrets refs
- Cold-start gotcha: needs `MinSize: 1` provisioned concurrency to avoid first-request OAuth 404
- In-memory tokens fine for 3 users; redeploys are rare
- Effort: ~1 day end-to-end (ECR push, App Runner config, Secrets Manager, Cloudflare CNAME `mcp.treemetrics.dev` → App Runner default URL, OAuth client redirect URI)
- Marginal cost: ~$25–50/mo (App Runner has a base + per-request pricing; small workloads land in this range)

### Option 2 — ECS Fargate, new dedicated cluster + new ALB + CDK

- Greenfield: new cluster, new ALB, new ACM cert, new CDK stack
- Matches the platform pattern but doesn't actually reuse anything
- Effort: 1–2 days CDK + verification
- Marginal cost: ~$22/mo ALB base + ~$10–15/mo Fargate task

### Option 3 — Reuse an existing Fargate ALB with path / host routing

Reviewer initially suggested `staging-hq-alb`, but **that ALB is EC2-targeted and currently unhealthy**, not Fargate. Real Fargate-fronting ALBs are `sintetic-be-production-alb`, `fs-service-staging-alb`, `geoserver-service-staging-alb` — each dedicated to one app with an app-specific cert. Adding a path/host rule means coupling an internal MCP tool to a production app's listener and cert. Possible but semantically wrong (e.g. `mcp.sintetic.treemetrics.com` is misleading; `mcp.treemetrics.com` would need a new SNI cert anyway, at which point Option 2 is barely more work). **Not recommended.**

### Option 4 — Colocate on existing EC2 + Cloudflare tunnel (matches existing pattern)

`treetops_backend` (t3.large) has the headroom to host a 100 MB Node container next to whatever it currently runs.
- `docker compose up -d`
- Add `mcp.treemetrics.dev` as a route on the existing `f6425610-…` named tunnel (no new tunnel, no new account access required)
- No inbound port, no ALB, no ACM, no Route53 — Cloudflare handles HTTPS and DNS
- Effort: ~1 hour. The "permission Alex is blocked on" does **not** apply here — that's for *Alex's personal* tunnel; org tunnel routes are managed by whoever runs `cloudflared` (japoveda).
- Cost: ~$0 (uses existing instance + free Cloudflare tunnel tier)
- Caveats: noisy-neighbour risk (need to check what `treetops_backend` runs); tied to that instance's lifecycle; not reflected in IaC unless we write it in
- Migration cost back to AWS later if scale or operational pressure justifies it: change one Cloudflare CNAME, push image to ECR, point at App Runner. Image is already containerised; nothing in Option 4 makes Option 1 harder later.

### Option 5 — Cloud Run + Firestore (upstream-supported path)

- One command: `gcloud run deploy --source .`
- Firestore token store ships in upstream code, no adapter to write
- ~$2–3/mo with `--min-instances=1`
- Cost of being off-platform: separate IAM, billing, monitoring, on-call surface in a different cloud — small at 3 users, real at scale
- Worth considering only if there is appetite for a non-AWS internal tool

## Recommendation

For this specific use case (3 users today, possibly company-wide later, no SLA, internal tool, soft deadline):

**Option 4 + in-memory tokens.** Clear primary.

Why it wins after stakeholder context:
- The "Cloudflare tunnel + `treemetrics.dev`" pattern is already the org's internal-tools pattern (climate-smart team uses it; japoveda operates `cloudflared`). Option 4 *is* on-pattern; the AWS-native paths are the off-pattern ones for internal tools.
- AWS is a soft preference ("everything else is there"), not a hard constraint. That preference doesn't justify ~1 day of work + ~$25–50/mo when migrating later is a CNAME swap.
- Scale is unknown but defer-able: the only thing scale really flips is the token store (in-memory → DDB adapter ~100 LOC). Build the simple one now, migrate when redeploys actually start hurting users.
- Effort is ~1 hour vs ~1 day. Cost is ~$0 vs ~$25–50/mo. Reversibility is cheap.

**Fallback if Option 4 is rejected for noisy-neighbour reasons:** spin up a small dedicated EC2 (e.g. t3.micro/small in eu-west-1) running `docker compose up -d` and `cloudflared`, still using the existing tunnel and `mcp.treemetrics.dev`. Keeps the on-pattern Cloudflare ingress, separates the lifecycle from `treetops_backend`. ~half a day, ~$8/mo.

**Fallback if "must be a managed AWS service" is asserted as a hard line:** Option 1 (App Runner) with `MinSize: 1`, in-memory tokens, Cloudflare CNAME `mcp.treemetrics.dev` → App Runner default URL. ~1 day, ~$25–50/mo.

**Reject:** Option 2 as the first move (over-spec for 3–N users), Option 3 (ALB reuse doesn't actually reuse anything cleanly), Option 5 (off-platform; no upside given Cloudflare path already exists in-org).

## Required regardless of host

- Set Google OAuth client to **Web application** type
- Authorised redirect URI = `${BASE_URL}/oauth/callback` for each environment
- Consent screen = **Internal** (Workspace-only, no verification review, no test-user list)
- Enable Docs / Sheets / Drive / Gmail / Calendar / Apps Script APIs on the GCP project
- Authorise the full scope list on the consent screen
- `ALLOWED_DOMAINS=treemetrics.com` as defence-in-depth
- Pin `JWT_SIGNING_KEY` so issued MCP tokens survive restarts
- Add cold-start mitigation note to `docs/deploy-aws.md` before merging the PR

## Stakeholder context (confirmed)

- **AWS framing**: soft preference ("where everything else is"), not a hard constraint. Insufficient to override an off-AWS path that matches the org's existing internal-tools pattern.
- **Cloudflare**: account exists, zone is `treemetrics.dev`, named tunnel `f6425610-…` already in production, japoveda operates `cloudflared`. Adding `mcp.treemetrics.dev` to the existing tunnel needs no new permissions. Alex's "Connector write permission" blocker is for his personal local-PC tunnel only — orthogonal to org-level deployment.
- **Scale**: 3 users today, possibly company-wide later, no timeline. Defer-able: scale only really affects the token-store decision. Ship in-memory now; add a DDB-style adapter (~100 LOC) when redeploys start being an annoyance.
- **Pattern**: the "Cloudflare-tunnel-on-`treemetrics.dev`" internal-tools pattern already exists (climate-smart's `*.treemetrics.dev` services). This service joins it rather than seeding a new one — no pattern-investment argument for Option 2.

## Required PR-level edits

- Replace the `aws apprunner` CLI deploy sketch with a `compose-on-EC2 + Cloudflare tunnel` deploy sketch (Option 4 path), pointing at the existing `f6425610-…` tunnel and `mcp.treemetrics.dev`.
- Drop the "AWS service: TBD" framing — the host decision is no longer "TBD AWS service", it's "Cloudflare tunnel on existing EC2, Option 1 (App Runner) is the documented escape hatch".
- Keep the cold-start / `MinSize: 1` note in the App Runner appendix (still applies to the escape-hatch path).
- Rename the doc — `deploy-aws.md` is now misleading. Suggest `deploy.md` with sections per option.
