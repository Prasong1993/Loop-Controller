# NEXUS — Error, Defect, and Limitation Report

Report ID: NEXUS-ERR-001  
Date: 2026-10-10  
Scope: repository baseline, initial controller increment and cross-platform feasibility. This is not a claim that device or production tests passed.

## Summary
- Core implemented: deterministic Python/SQLite state machine, evidence and execution gates, route selection, audit events and checkpoint creation.
- API and tests are included in source. Test results are not claimed until execution/CI is observed.
- No mobile client apps are implemented; no physical Android/iOS/iPadOS testing has been run.
- Production authentication, TLS, deployment and credentials are not configured.
- Official platform guidance confirms that mobile background execution is constrained.

## Findings
| ID | Severity | Finding | Status | Action |
|---|---|---|---|---|
| NXR-E001 | High | Native Android/iOS/iPadOS client apps not implemented | OPEN | Implement clients after workflow and permissions are validated |
| NXR-E002 | High | Physical-device tests not performed | NOT RUN | Test supported OS/device matrix and record evidence |
| NXR-E003 | High | Production authentication/TLS/secrets not configured | OPEN | Add auth, secrets manager and security review before public exposure |
| NXR-E004 | Medium | ChatGPT connected-app availability for this account unknown | UNKNOWN | Verify actual account/interface |
| NXR-E005 | Medium | Repository is named Loop-Controller, not NEXUS | OPEN | Rename through repo settings/admin UI or supported API |
| NXR-E006 | Medium | CI result not confirmed | NOT RUN | Inspect GitHub Actions after commit |
| NXR-E007 | High | Production-grade identity, authorization and tenant isolation incomplete | OPEN | Add auth principal and adversarial isolation tests |
| NXR-E008 | Medium | Checkpoint creation exists; restore/resume not implemented | OPEN | Implement restore semantics and recovery tests |
| NXR-E009 | Medium | VERIFIED evidence currently requires a URL but does not fetch/verify its content | OPEN | Add source/quote/section/freshness/reviewer validation |
| NXR-E010 | Medium | Router is a selector, not a provider-adapter execution system | OPEN | Define adapters, health checks, idempotency and error contracts |

## Error-handling contract
- Illegal state transition: reject with InvalidTransition.
- Policy gate failure: reject with PolicyDenied.
- Unknown task/project: reject with ValueError (initial HTTP wrapper maps this to HTTP 409; refine to 404).
- Warning, missing capability/permission, or unapproved paid cost: block route; no blind retry.
- Unexpected runtime failure: production redacted logging and persistent error codes still need hardening.

## Verification status
- Source files: will be verified by GitHub read-back.
- Python unit tests: INCLUDED; execution status not yet claimed.
- GitHub Actions: CONFIGURED; result not yet claimed.
- Security review: NOT RUN.
- Native device tests: NOT RUN.
- Production readiness: NOT READY.
