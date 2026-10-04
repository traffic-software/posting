# SeleniumBase migration plan

Status: proposal only; no application or dependency changes made.
Reviewed: 2026-10-04. Compatibility and runtime behavior remain to be tested.

## Decision

Use a staged SeleniumBase `Driver()` integration inside the existing task-scoped runtime, not a conversion of the API/worker into `BaseCase` tests. Keep the raw Selenium backend as an explicit rollout fallback. Initially preserve all tool behavior; adopt higher-level helpers only where contract tests prove equivalence.

The official migration tutorial demonstrates pytest/unittest tests evolving toward BaseCase. This application instead runs browser tasks from a background worker. SeleniumBase documents a plain-Python Driver format returning a WebDriver-compatible object, making that the best initial candidate. Driver creation alone will not automatically improve existing action waits or convert the application to SeleniumBase helpers.

## Observed project facts

- [worker](../app/worker.py) calls the task runner from a thread. [agent](../app/agent.py) obtains `session.driver` and `session.desktop` from `local_browser`, then supplies them to `browser_tools`.
- [runtime](../app/browser_runtime.py) owns the exclusive runtime lock, Xvfb, Openbox, temporary profile, ChromeDriver service, viewer and cancellation cleanup. It explicitly avoids runtime driver downloads.
- [tools](../app/selenium_tools.py) enforce public destinations, write permissions, credential origins, redaction and policy stops. Production clicks and typing use the desktop adapter; raw WebDriver writes also exist as a fallback.
- [readiness](../app/element_readiness.py) checks coverage, visibility, disabled/readonly state and cancellation with a task-bounded polling loop. It retries discovery, not writes.
- [desktop adapter](../app/desktop_tools.py) uses focus, live-element geometry and display mapping. Headless conversion is not behavior-preserving.
- [Dockerfile](../Dockerfile) specifies Python 3.14.8, Chrome for Testing / ChromeDriver 154.0.8037.92, a non-root runtime and one Uvicorn worker. These are observed pins, not independently certified available/compatible versions.
- [requirements input](../requirements.txt) and [lock](../requirements.lock) are separate; the image installs the lock. The lock records `uv pip compile --universal` as its generation method.
- [README](../README.md) separates the new API from the legacy GCW/ps_lib worker. Initial scope is the new API, not migration of that legacy subsystem.

## Stage 1 — baseline and compatibility gate

1. Run the existing runtime/tool/readiness unit tests before changing behavior; record pre-existing failures separately.
2. Select and pin a SeleniumBase release after checking its declared Python, Selenium and pytest constraints against this project's pins. Do not invent a version or independently upgrade Selenium without resolving the combined requirements.
3. Regenerate the lock with the existing workflow and inspect dependency churn. Retain direct Selenium dependency declarations while application modules import Selenium APIs.
4. Build a minimal Linux-container proof of concept from the actual worker thread, using the existing Xvfb/Openbox display and a fresh profile.
5. Verify non-root startup, fixed window geometry, desktop focus, browser/driver versions and the actual service executable path.

**Blocking gate:** prove that SeleniumBase uses the preinstalled pinned driver without downloading at task startup. `driver_version` chooses a version; it is not proof that `settings.chromedriver_binary` is honored. Investigate the chosen release's driver discovery/cache behavior. Pre-provision its required location at image build time if supported; keep one explicit source of truth. If the contract cannot be preserved through supported integration, stop rollout and retain the existing backend rather than monkeypatching package internals.

## Stage 2 — runtime-only migration

- Add a small driver factory boundary in [runtime](../app/browser_runtime.py); keep `LocalBrowserSession(driver, desktop)` and the caller interface stable.
- Add a validated backend setting in [config](../app/config.py), initially defaulting to Selenium; SeleniumBase is opt-in during validation.
- Map browser binary, profile, headed mode, Chromium arguments and timeouts explicitly. SeleniumBase supports binary/profile/version options, but exact launch defaults must be audited for the selected release. Explicitly preserve headed operation on Xvfb and inspect security-related browser flags.
- Keep Xvfb ownership in the application. Do not introduce a second display manager or replace the live viewer.
- Keep normal WebDriver mode: no UC/stealth/CDP migration, proxy addition or CAPTCHA automation.
- Preserve cancellation, idempotent shutdown, profile deletion, viewer teardown, Xlib rebinding and lock release. Cover construction failure before a driver is returned as well as quit/service-stop failures.
- Do not assume DriverContext automatic quit replaces the current cancellation callback: explicit resource ownership is required here.

## Stage 3 — selective helper adoption

| Existing operation | Proposed treatment |
|---|---|
| Navigation | Keep URL policy checks before/after navigation; compare candidate helper behavior before replacing `get`. |
| Read-only text/element access | Pilot helpers behind the adapter, preserving output bounds and redaction. |
| Readiness polling | Retain the custom loop until equivalent cancellation, coverage, readonly and deadline behavior is demonstrated. |
| Click / fill / hover / keys | Keep the desktop path and live-target checks; no mechanical replacement with SeleniumBase click/type. |
| Credential and TOTP entry | Preserve dedicated tools, exact-origin checks, expiry, no-secret output and no automatic resubmission. |
| DOM / form discovery | Preserve existing scripts and selectors initially. |

The tutorial's `type()` performs waiting, clearing, typing and potentially submitting when text ends in a newline. That is not interchangeable with this project's guarded input sequence. Audit helper retries, implicit navigation waits and exception handling before allowing helpers to perform writes. Every timeout must fit the remaining task budget; a timeout must not be reported as “no input occurred” after a possible write.

## Stage 4 — validation matrix

Run focused tests first, then the full suite before changing the default backend:

- [runtime unit tests](../tests/test_browser_runtime.py): startup failure, quit failure, owned service cleanup and lock release; parameterize factory mocks for both backends.
- [tool tests](../tests/test_selenium_tools.py), [readiness tests](../tests/test_element_readiness.py), [login tests](../tests/test_login_forms.py), [TOTP tests](../tests/test_totp_tools.py): permission parity, stale/covered controls, cancellation, origin restrictions, redaction and single-submit behavior.
- [desktop runtime tests](../tests/test_desktop_runtime.py), [desktop browser tests](../tests/test_desktop_browser_tools.py): focus, typing, scrolling and geometry parity.
- [local integration](../tests/test_local_browser_integration.py): real Linux display, repeated sessions, distinct profiles, actual driver path and ordinary WebDriver behavior. Preserve the existing `navigator.webdriver` and driver-path expectations unless a separately justified contract change is approved.
- [viewer integration](../tests/test_display_viewer_integration.py): browser visible in the same display; disconnect/cleanup on completion and cancellation.
- [agent tests](../tests/test_agent.py), [API tests](../tests/test_api.py), [account task tests](../tests/test_account_tasks.py): unchanged tool schemas, API results and shutdown behavior.
- Add offline-startup coverage with preinstalled binaries, cancellation during waiting/startup, and worker-thread repeated-task checks for leaked global state.
- Use synthetic pages and mock model replies, not real accounts or external posting actions. Linux integration is explicitly opt-in; Windows unit success alone is insufficient.

**Release acceptance:** no regression in permissions/results; no duplicate submissions; no runtime driver downloads; no surviving owned browser/display processes or profiles; viewer and cancellation remain correct. Compare startup time and image size against baseline; no assumed speed or flakiness improvement.

## Stage 5 — rollout and rollback

1. Enable SeleniumBase only in a staging image after all gates pass.
2. Exercise synthetic browse, authorized form, cancellation and viewer flows.
3. Change the backend default only after parity is demonstrated; keep the Selenium fallback for the initial rollout.
4. Roll back by selecting the previous backend or previous image for subsequent tasks. Never automatically retry a failed task with another backend: its writes may already have happened.
5. Update [README](../README.md), [.env.example](../.env.example), and directly affected deployment documentation with the backend setting, pinned dependencies and verification procedure.

## Sources and limitations

- [Official migration tutorial](https://seleniumbase.io/examples/migration/raw_selenium/ReadMe/): test-oriented progression and action semantics.
- [Official syntax formats](https://seleniumbase.io/help_docs/syntax_formats/): BaseCase, SB, DriverContext and direct Driver integration.
- [Official repository](https://github.com/seleniumbase/SeleniumBase).
- [Driver manager source](https://github.com/seleniumbase/SeleniumBase/blob/master/seleniumbase/plugins/driver_manager.py): inspected option names and headed-mode handling; master is mutable, so recheck the selected release.

This plan is based on source inspection and official documentation, not a completed migration experiment. No dependencies were installed, containers launched, or tests run for this planning task. The driver provisioning contract and release compatibility remain the first implementation gates.
