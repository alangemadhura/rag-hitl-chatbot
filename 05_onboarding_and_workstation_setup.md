# Employee Onboarding & Workstation Setup SOP

## Section 1: Pre-Day-1 Provisioning Checklist
IT Service Desk prepares standard accounts and hardware **at least 3 business days** before a new hire's start date:
1. Provision corporate SSO identity, email account, and baseline workspace groups.
2. Assign standard laptop configuration (encrypted disk, endpoint detection agent, and company password manager).
3. Grant baseline role-based team access based on manager intake form (excluding privileged production roles).

## Section 2: Day-1 Verification & Troubleshooting
- New hires complete MFA enrollment and verify VPN + SSO sign-in on Day 1.
- If a laptop fails to boot, MDM enrollment stalls, or an account is locked out, log a ticket with the hardware serial number or employee username and route to `it-service-desk-tier1` (or `P2` if blocking Day-1 orientation tasks).

## Section 3: Offboarding & Asset Return
- When an employee departs, revoke SSO/cloud sessions and disable active tokens within **2 hours** of offboarding notice (immediately for involuntary terminations).
- Collect company-issued laptops and security keys within **5 business days** and wipe storage using approved media sanitization procedures.
