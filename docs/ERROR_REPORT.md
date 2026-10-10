# NEXUS — Error, Defect, and Limitation Report

Report ID: NEXUS-ERR-001  
Date: 2026-10-10  
Scope: repository baseline, controller increment, and ChatGPT-app-first integration feasibility. This is not a claim that ChatGPT integration or production tests passed.

## Summary
- Core implemented: deterministic Python/SQLite state machine, evidence and execution gates, route selection, audit events and checkpoint creation.
- API and tests are included in source. Test results are not claimed until execution/CI is observed.
- Separate native mobile clients are intentionally out of scope. Physical Android/iOS/iPadOS tests are not a gate for the current ChatGPT-app-first scope; real ChatGPT integration is not configured and is NOT RUN.
- Production authentication, TLS, deployment and credentials are not configured.
- Official platform guidance confirms that mobile background execution is constrained.

## Findings
| ID | Severity | Finding | Status | Action |
|---|---|---|---|---|
| NXR-E001 | Low | Native Android/iOS/iPadOS client apps not implemented | OUT OF SCOPE | Do not implement unless native/OS-specific functionality is approved |
| NXR-E002 | Low | Physical-device tests not performed | NOT REQUIRED FOR CURRENT SCOPE | Only test devices when native/OS-specific behavior is added or a device-specific issue appears |
| NXR-E003 | High | Production authentication/TLS/secrets not configured | OPEN | Add auth, secrets manager and security review before public exposure |
| NXR-E004 | High | ChatGPT integration availability and live round-trip not confirmed | NOT RUN / UNKNOWN | Configure a supported connector/API integration and execute acceptance tests in the actual ChatGPT app/account |
| NXR-E005 | Medium | Repository is named Loop-Controller, not NEXUS | OPEN | Rename through repo settings/admin UI or supported API |
| NXR-E006 | Low | CI result not confirmed | SUPERSEDED BY CI EVIDENCE | See latest successful GitHub Actions run below |
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


## CI update — 2026-10-10 (supersedes NXR-E006's earlier NOT RUN status)
GitHub Actions run #9 completed successfully for commit 4b61e19daa6301ebbe70595b8b44e1581074df88. All three matrix jobs passed: Python 3.11, 3.12, and 3.13. Each job completed dependency installation, compileall, and unittest discovery successfully.
Run: https://github.com/Prasong1993/Loop-Controller/actions/runs/38011520599

Updated statuses:
- Source read-back: VERIFIED.
- CI compile + unit test workflow: PASS on Python 3.11/3.12/3.13.
- Security review, production deployment, auth/TLS, checkpoint restoration and ChatGPT-app integration: NOT RUN / OPEN.
- Physical Android/iOS/iPadOS device testing: not required for current scope; becomes applicable only if native or OS-dependent functionality is introduced.
- Overall production readiness: NOT READY.

## Scope correction — ChatGPT-app-first (2026-10-10)
The earlier wording treated native mobile clients and physical device tests as required gaps. That was not aligned with the intended product. NEXUS is intended to be used through the ChatGPT application across Android, iOS and iPadOS, not through separate native NEXUS apps. Therefore native clients and device-matrix tests are OUT OF SCOPE for the current increment.

**New release acceptance blocker:** the NEXUS controller is currently repository code/local FastAPI, not a deployed and connected ChatGPT integration. The following remain NOT RUN until the integration is actually configured: connector discoverability for the user's account, authorized task create/read round-trip, policy-denial behavior, audit retrieval, and warning/error handling. A green CI workflow does not prove ChatGPT integration works.
