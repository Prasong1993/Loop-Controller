# NEXUS — Platform Compatibility Matrix

Status: revised for ChatGPT-app-first integration. ChatGPT connector integration NOT RUN; native device testing is NOT REQUIRED for the current scope.
Scope: using NEXUS through the ChatGPT application on Android, iOS and iPadOS, plus web/server runtime.

## Design rule
NEXUS is intended to be accessed through the ChatGPT application on Android, iOS and iPadOS using a supported connected app/tool/API integration. It is not a plan to build separate native mobile clients. The ChatGPT app is the user interface; NEXUS controller logic must run in an accessible, secured runtime and be exposed through an integration that the user's ChatGPT account actually supports. That integration is NOT YET CONFIGURED.

| Capability | Android | iOS | iPadOS | Server/web |
|---|---|---|---|---|
| ChatGPT app/integrations | Target interface; account and connector capability must be checked | Target interface; account and connector capability must be checked | Target interface; account and connector capability must be checked | Controller/API must be deployed and securely reachable |
| Background work | WorkManager is scheduled/opportunistic; foreground service requires visible notification and applicable declarations/permissions | Background tasks are system-managed and time-limited | Same Apple background-task model; verify supported OS versions | Server jobs subject to host/provider limits |
| Authoritative workflow state | Do not rely on device as sole store | Same | Same | Preferred authoritative state |
| API secrets | Never ship server API keys in client app | Same | Same | Use environment/secret manager with access control |
| Native UI automation | Device permissions/tooling constrained; not guaranteed by ChatGPT | Requires supported tooling and permissions; not assumed | Requires supported tooling and permissions; not assumed | Use authorized APIs/browser automation where supported |

## Operational policy
1. Server-side state is authoritative.
2. Client background events are hints, not guarantees; jobs must be idempotent or duplicate-protected.
3. For the current ChatGPT-app-first scope, test the integration contract and real ChatGPT round-trip when configured. Physical-device tests are conditional, not a universal release gate; require them only for native/OS-specific behavior or a device-dependent defect.
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

## Current acceptance approach (supersedes blanket device-test requirement)
- Native Android/iOS/iPadOS applications are OUT OF SCOPE unless a later approved requirement adds native functionality.
- Do not require a physical test on every phone/tablet merely because ChatGPT is accessed from that device. Use automated controller tests and an actual ChatGPT-app integration acceptance test.
- ChatGPT integration acceptance checks: (1) integration is available to the user's account/interface, (2) least-privilege authorization works, (3) create/read a test task round-trip, (4) policy denial blocks an unauthorized action, (5) audit record is retrievable, and (6) errors/warnings do not cause blind retries.
- Current integration status: NOT RUN / NOT CONFIGURED. The repository's local FastAPI service is not yet deployed or connected to ChatGPT. Do not report ChatGPT-app compatibility as PASS until a real round-trip has evidence.
- Device/OS tests become required only if a native app, OS API, local file/device access, push notification, or platform-specific background behavior is introduced.
