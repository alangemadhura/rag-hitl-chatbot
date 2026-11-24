# Incident Response Runbook — Production Services

## Section 1: Severity Classification & Response SLAs
Incidents are classified into four severity tiers based on customer and operational impact:
- **SEV-1 (Critical):** Complete outage of a production service, data loss/corruption, or active security breach. Initial acknowledgment within **10 minutes**; status updates every **30 minutes**.
- **SEV-2 (High):** Major degradation affecting core workflows or a large subset of users with a partial workaround. Initial acknowledgment within **20 minutes**; status updates every **60 minutes**.
- **SEV-3 (Medium):** Minor functional defect or degraded non-critical component with minimal impact. Initial acknowledgment within **4 hours**; daily updates.
- **SEV-4 (Low):** Cosmetic issue, documentation gap, or enhancement request. Initial acknowledgment within **2 business days**.

## Section 2: Triage & War Room Mobilization
1. Confirm alert signal in monitoring dashboards and check recent deployments in the last 2 hours.
2. Assign an **Incident Commander (IC)** and a **Communications Lead** for all SEV-1 and SEV-2 incidents.
3. Open a dedicated incident channel (`#inc-YYYYMMDD-short-title`) and log timeline events in UTC.
4. Avoid running unverified destructive commands directly on primary production nodes during active triage.

## Section 3: Escalation & Service Restart Procedures
- **Database & Stateful Service Escalation:** If connection pool exhaustion, replication lag above 30 seconds, or primary failover issues occur, escalate immediately to the **Database Reliability Engineering (DBRE)** on-call rotation and page the Engineering Manager if downtime exceeds 15 minutes.
- **Application Pod / Service Restart:** Before restarting a production service or worker pool, capture diagnostic logs and thread/heap snapshots if available. Rolling restarts are preferred over full-cluster restarts. Any production server or database restart that may drop active sessions requires **explicit human approval** before execution.

## Section 4: Post-Incident Review (PIR)
- A blameless Post-Incident Review must be scheduled within **48 hours** of resolution for all SEV-1 and SEV-2 incidents.
- Action items must include a clear owner, target completion date, and preventive safeguard (alerting, automated test, or runbook update).
