# NEXUS — Platform Compatibility Matrix

Status: evidence-informed design; physical-device validation NOT RUN.
Scope: Android, iOS, iPadOS, web and server/CI.

## Design rule
NEXUS core policy/state machine runs in a controlled server/runtime independent of mobile OS. Clients are interfaces and optional best-effort workers, not reliable long-running execution engines.

| Capability | Android | iOS | iPadOS | Server/web |
|---|---|---|---|---|
| ChatGPT app/integrations | App exists; exact availability depends on account, version and interface | App exists; exact availability depends on account, version and interface | Verify iPad-specific availability and feature parity | Availability depends on service/account |
| Background work | WorkManager is scheduled/opportunistic; foreground service requires visible notification and applicable declarations/permissions | Background tasks are system-managed and time-limited | Same Apple background-task model; verify supported OS versions | Server jobs subject to host/provider limits |
| Authoritative workflow state | Do not rely on device as sole store | Same | Same | Preferred authoritative state |
| API secrets | Never ship server API keys in client app | Same | Same | Use environment/secret manager with access control |
| Native UI automation | Device permissions/tooling constrained; not guaranteed by ChatGPT | Requires supported tooling and permissions; not assumed | Requires supported tooling and permissions; not assumed | Use authorized APIs/browser automation where supported |

## Operational policy
1. Server-side state is authoritative.
2. Client background events are hints, not guarantees; jobs must be idempotent or duplicate-protected.
3. Mark platform features VERIFIED only when official documentation supports the claim; device tests are required where practical.
4. Do not claim ChatGPT can control all device apps, access arbitrary local data, or run unattended indefinitely.
5. Paid fallback requires explicit policy and budget approval.
6. If a platform lacks a capability, return BLOCKED or use an approved server alternative.

## Official sources inspected on 2026-10-10
- Android Developers, Foreground services overview: https://developer.android.com/develop/background-work/services/fgs
- Apple Developer, Choosing Background Strategies: https://developer.apple.com/documentation/backgroundtasks/choosing-background-strategies-for-your-app
- OpenAI API, Function calling: https://developers.openai.com/api/docs/guides/function-calling
- OpenAI Help Center, Connected apps: https://help.openai.com/en/articles/11487775-connected-apps-in-chatgpt
- NASA, System Design Processes: https://www.nasa.gov/reference/4-0-system-design-processes/

## Verified findings and limitations
- VERIFIED: Android foreground services have explicit usage/declaration rules; they are not general permission for invisible unrestricted automation.
- VERIFIED: Apple directs developers to select specific background execution strategies; background execution is system-managed and not an indefinite runtime guarantee.
- VERIFIED: OpenAI function calling connects models to application-defined tools; the application handles the tool calls.
- VERIFIED: ChatGPT connected-app availability depends on app, plan, region, workspace, role, model and interface.
- VERIFIED: NASA's system design reference exists as a process-design source; this does not certify NEXUS or imply NASA endorsement.
- UNKNOWN: User-account-specific app availability, physical device tests, store approval, provider quotas, and exact OS-version behavior.
