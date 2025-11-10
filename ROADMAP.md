# Flowork ROADMAP
_Last updated: 2025-11-07 (Asia/Jakarta)_

> This roadmap is source-of-truth for MVP → Beta → GA. It encodes **SLOs, milestones, scaling rules, and guardrails** so the system stays **secure, robust, and lightweight**.

## 0) Vision & Non‑Goals
**Vision:** Millions of users can access Flowork with near-zero incremental cost: GUI on Cloudflare Pages, user-hosted Gateway/Core, SQLite-based queues, and **secure token tunnels** across trust boundaries.

**Non‑Goals (for MVP):**
- No paid multi-region replication (stick to single region + backups).
- No PostgreSQL dependency (keep SQLite sharded).
- No vendor lock-in to any LLM provider.

## 1) Architecture Overview
```
[Browser GUI (Cloudflare Pages)]
        | HTTPS + message signing (ECDSA/ethers)
        v
[Gateway/API (user-hosted, FastAPI/Socket.IO)]
        | Zero-trust: JWT per user + X-Engine-Token per engine
        | Queue (SQLite sharded): enqueue/claim/finish
        v
[Core Engines (user-hosted, N workers)]
        | Pull/claim jobs via internal API
        v
[Providers: LLMs, tools]
```
**Multi-tenancy:** One user ↔ many engines; one engine ↔ many users. Isolation enforced by **engine token** + per-user JWT + job scoping.

## 2) SLOs & KPIs (MVP → GA)
**User-facing SLOs**
- p95 end-to-end latency (GUI→Gateway→Engine→Gateway→GUI): **≤ 3.0s** (MVP), **≤ 1.5s** (GA)
- Error rate (HTTP 5xx or job failed): **≤ 1%** p95 rolling 15 min
- Availability (Gateway): **≥ 99.9%** monthly

**System KPIs**
- Queue depth p95: **≤ 2× target_jit** (target jitter = 250ms)
- Job start delay p95 (enqueue→claim): **≤ 500ms**
- Worker utilization target: **65–80%**

## 3) Scaling & Backpressure Rules
**Env knobs** (already exist): `CORE_MAX_WORKERS`, `SLO_TARGET_LATENCY`, `HEADROOM_FACTOR`.

**Autoscaling policy (single host, N workers):**
- If `p95_queue_latency > 3 × target_latency` for 3 consecutive windows ⇒ **+1 worker** (up to max).
- If `p95_queue_latency < 0.3 × target_latency` for 6 consecutive windows and `utilization < 50%` ⇒ **−1 worker** (respect min).
- Always keep `HEADROOM_FACTOR ≥ 1.3` vs observed peak RPS.

**Admission control & drain:**
- When `queue_depth > hard_cap` ⇒ return `429` with `Retry-After` and advertise **/drain** state for rolling upgrades.
- Idempotency key required for duplicate suppression.

**Horizontal scale (multi-process/multi-host):**
- Shard SQLite per engine. Engines are stateless except local cache; scale by spawning more engine workers and/or more engine instances per shard.

## 4) Security Guardrails (see SECURITY.md)
- Token tunnel: `X-Engine-Token` scoped per engine (no repo persistence).
- GUI handshake uses ECDSA message signing (ethers) recovered at Gateway.
- Admin tokens have **short TTL** and **scopes** (capabilities only).
- Cloudflare edge rate-limiting: per IP + per user bucket.

## 5) Observability (MVP→GA)
- **Logs:** JSON with fields `{trace_id, user_id, engine_id, job_id, ip, route, status, latency_ms}`.
- **Metrics:** queue depth, claim latency p50/p95, worker busy ratio, error rate.
- **Traces:** propagate `traceparent` through GUI→Gateway→Engine calls.
- **Audit:** auth events, token rotations, admin operations (immutable store, 90-day retention).

## 6) Milestones & Timeline
### Phase 1 — MVP Hardening (by 2025-11-21)
- [ ] Cloudflare rate-limit rules (per IP + per user header)
- [ ] Idempotency key mandatory for /jobs
- [ ] JSON log fields standardization
- [ ] Integration tests: socket handshake; enqueue→claim→finish; whitelist sync

### Phase 2 — Observability & Ops (by 2025-12-05)
- [ ] Metrics export (Prom/OTLP) + minimal Grafana dashboard
- [ ] Alerting: p95 latency, error rate, queue depth
- [ ] Rolling upgrade playbook: drain, canary 10%, full rollout

### Phase 3 — Security & Scale (by 2025-12-19)
- [ ] Admin token scopes + TTL 15m
- [ ] Key rotation schedule (monthly) + pre-prod rehearsal
- [ ] DoS budget guard (token bucket) aligned with SLOs

### Phase 4 — Beta → GA (by 2026-01-16)
- [ ] Public status endpoint v2: per-engine health and capacity hints
- [ ] Performance tuning (p95 ≤ 1.5s), cold-start < 300ms
- [ ] DR drill (restore from snapshot), RPO ≤ 24h, RTO ≤ 2h

## 7) Testing Strategy
- **Unit:** queue ops, token signing/verification, idempotency.
- **Integration:** end-to-end job flow; GUI handshake; rate-limit behavior.
- **E2E:** scripted browser test hitting Cloudflare Pages → Gateway → Engine.
- **Security tests:** JWT expiry/refresh, replay protection, origin spoofing, signature failure.

## 8) Operational Playbooks
- **Deploy:** enable edge rules → canary gateway (10%) → monitor → roll forward.
- **Rollback:** flip traffic to previous build; preserve queue; reconcile jobs by idempotency.
- **Incident:** severity levels; oncall rotation; comms template; postmortem checklist.

## 9) Risks & Mitigations
| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Hot shard (SQLite) | Latency spike | Med | Per-engine sharding + cap per shard + worker backoff |
| Token leakage | High | Low | Secrets scanning in CI; never commit tokens; monthly rotation |
| Provider outage | Med | Med | Retries with jitter; fallback provider adapters |
| DoS surge | High | Med | Edge rate-limits + 429 budget + admission control |

## 10) File locations (Windows repo)
- `C:\FLOWORK\ROADMAP.md`
- `C:\FLOWORK\SECURITY.md` (see below)
