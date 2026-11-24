# Service Desk Ticketing & Escalation Guide

## Section 1: Ticket Priorities & Routing Queues
Tickets must be assigned an accurate priority and routed to the appropriate queue so work is triaged without delay:
- **P1 (Urgent):** Production outage or security incident impacting multiple users. Route to `it-incident-oncall`.
- **P2 (High):** Significant workflow blockage or urgent access/hardware request blocking a deadline. Route to `it-service-desk-tier2`.
- **P3 (Normal):** Standard software installation, account setup, or non-urgent troubleshooting. Route to `it-service-desk-tier1`.
- **P4 (Low):** General inquiries, how-to questions, or minor requests. Route to `it-general-support`.

## Section 2: Required Ticket Fields
When creating or escalating a ticket, include:
1. **Summary / Title:** Concise description of the issue or request.
2. **Priority (`P1`–`P4`) & Queue:** Clear urgency and owning team.
3. **Impact & Scope:** Affected system, user count, and business impact.
4. **Reproduction Steps / Context:** Error messages, timestamps, or relevant policy/runbook references.

## Section 3: Escalation Thresholds
- Escalate a ticket from Tier 1 to Tier 2 if unresolved after **2 business hours** for P3 requests or **30 minutes** for P2 requests.
- Any P1 ticket or external vendor escalation requires explicit confirmation of priority, target queue, and impact summary before submission.
