# Change Management & Deployment Standard

## Section 1: Change Categories
- **Standard Changes:** Pre-approved, low-risk, repeatable changes following a documented runbook (e.g., non-breaking config flag updates, scheduled log rotation).
- **Normal Changes:** Planned code releases, schema migrations, or infrastructure updates requiring peer code review and CI verification.
- **Emergency Changes:** Urgent fixes required to resolve or mitigate an active SEV-1/SEV-2 incident outside normal release windows.

## Section 2: Release Windows & Freeze Periods
- Standard production deployments are permitted **Tuesday through Thursday, 09:00–17:00 UTC**.
- **Change Freeze Periods:** No non-emergency production releases are allowed during major retail/peak traffic windows, company holiday freezes, or the final **48 hours** of each calendar quarter unless signed off by the VP of Engineering.

## Section 3: Rollback & Verification Checklist
1. Verify automated unit, integration, and migration dry-run checks have passed.
2. Confirm a tested rollback plan or feature-flag kill switch is ready prior to deployment.
3. Monitor error rates, p95/p99 latency, and saturation metrics for at least **20 minutes** post-release.
4. If error rates exceed baseline thresholds or critical health checks fail, execute rollback promptly and open an incident ticket if customer impact occurred.
