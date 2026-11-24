# Access Control & Security Policy

## Section 1: Principle of Least Privilege (PoLP)
All employees, contractors, and automated service accounts must be granted only the minimum permissions necessary to perform their assigned duties. Standing administrative access to production environments is prohibited by default.

## Section 2: Just-in-Time (JIT) Privileged Access
- Engineers requiring elevated privileges (`prod-db-readonly`, `k8s-admin`, or `iam-elevated`) must request **Just-in-Time (JIT)** access through the Identity & Access Management (IAM) portal.
- Standard JIT sessions expire automatically after **4 hours** (maximum **8 hours** with manager approval).
- Every JIT elevation request is logged with requester identity, ticket reference, justification, and expiration timestamp.

## Section 3: Authentication, MFA & Secret Hygiene
- Multi-Factor Authentication (MFA) via hardware security keys or approved authenticator apps is mandatory for all SSO, VPN, source control, and cloud console logins.
- Hardcoding API keys, passwords, private certificates, or database credentials in source code, config files, or chat prompts is strictly forbidden.
- Rotate compromised or suspected leaked credentials within **1 hour** of discovery and notify Security Operations (`#sec-ops`).

## Section 4: High-Risk Action Approval Rules
Automated assistants and scripts may draft or propose operational changes, but **human sign-off is mandatory** before executing high-risk actions, including:
- Granting or revoking production IAM/admin roles.
- Restarting production servers, load balancers, or database instances.
- Escalating critical tickets to external vendors or executive on-call chains.
