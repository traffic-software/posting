# SeleniumBase migration implementation record

Updated: 2026-10-04. SeleniumBase **4.55.0** normal headed Chrome `Driver()` is the sole browser factory. There is no backend selector, raw-Selenium fallback, UC or CDP mode. This record supersedes the earlier blocked-rollout proposal.

## Verified validation results

- Full host regression suite: **311 passed, 5 skipped**; focused runtime/tools suite: **99 passed**.
- Linux integration using the existing `posting:seleniumbase-smoke` image with current application/tests mounted read-only and `--network none`: **4 browser tests passed**, including repeated sessions; **1 viewer integration test passed**.
- A fresh build of the current Dockerfile failed during Debian package downloads with HTTP 400 for `libxcb-dri3-0` and `python3-chardet`, before the application dependency layer. Therefore the current clean image build is not certified by these results; Linux results above use the available smoke image.

## Decision and accepted security tradeoff

The user explicitly accepted SeleniumBase's known upstream sandbox and certificate-error behavior and requested this migration. This is **not security parity** with the previous raw Selenium launcher.

- Official [release metadata](https://pypi.org/pypi/seleniumbase/4.55.0/json) declares Python `>=3.10`, Selenium `==4.50.0`, and pytest `==9.1.1` on Python `>=3.11` (`==8.4.2` on Python 3.10). Keep the pinned input and regenerated lock aligned; the image installs the lock.
- The pinned [Driver signature](https://github.com/seleniumbase/SeleniumBase/blob/v4.55.0/seleniumbase/plugins/driver_manager.py#L67-L117) marks `no_sandbox` deprecated. Passing `no_sandbox=False` does not restore the Linux sandbox.
- The pinned [Chrome launcher](https://github.com/seleniumbase/SeleniumBase/blob/v4.55.0/seleniumbase/core/browser_launcher.py#L2669-L2682) adds certificate/SSL-error bypass flags in normal non-UC mode and `--no-sandbox` on Linux. `enable_ws=True` does **not** restore sandboxing or TLS certificate validation.
- No package monkeypatch, conflicting argument workaround, UC/CDP mode, CAPTCHA bypass or additional container security relaxation is part of this migration. Existing container restrictions and application guards remain necessary but cannot replace the lost browser protections.

Use the plain-Python `Driver()` inside the existing task-scoped runtime, not `BaseCase`, `SB` or a second display manager. Returning a WebDriver-compatible driver preserves the caller interface; it does not automatically migrate tool waits or actions to SeleniumBase helpers. Broader helper adoption remains deferred.

## Observed project facts

- [worker](../app/worker.py) calls the task runner from a thread. [agent](../app/agent.py) obtains `session.driver` and `session.desktop` from `local_browser`, then supplies them to `browser_tools`.
- [runtime](../app/browser_runtime.py) owns the exclusive runtime lock, Xvfb, Openbox, temporary profile, ChromeDriver service, viewer and cancellation cleanup. It explicitly avoids runtime driver downloads.
- [tools](../app/selenium_tools.py) enforce public destinations, write permissions, credential origins, redaction and policy stops. Production clicks and typing use the desktop adapter; raw WebDriver writes also exist as a fallback.
- [readiness](../app/element_readiness.py) checks coverage, visibility, disabled/readonly state and cancellation with a task-bounded polling loop. It retries discovery, not writes.
- [desktop adapter](../app/desktop_tools.py) uses focus, live-element geometry and display mapping. Headless conversion is not behavior-preserving.
- [Dockerfile](../Dockerfile) specifies Python 3.14.8, Chrome for Testing / ChromeDriver 154.0.8037.92, a non-root runtime and one Uvicorn worker. These are observed pins, not independently certified available/compatible versions.
- [requirements input](../requirements.txt) and [lock](../requirements.lock) are separate; the image installs the lock. The lock records `uv pip compile --universal` as its generation method.
- [README](../README.md) separates the new API from the legacy GCW/ps_lib worker. Initial scope is the new API, not migration of that legacy subsystem.

## Implemented runtime and driver provisioning contract

- SeleniumBase is pinned to **4.55.0**. Direct Selenium imports remain supported; dependency resolution belongs in both [requirements input](../requirements.txt) and [lock](../requirements.lock).
- Docker provisions the package-local `seleniumbase/drivers/chromedriver` slot as a root-owned symlink to `/usr/bin/chromedriver`, which points to the installed Chrome for Testing driver. The non-root worker does not patch, copy or replace the system driver. Docker sets `SE_OFFLINE=true` and `SE_CHROMEDRIVER=/usr/bin/chromedriver` to prevent Selenium Manager fallback downloads; package-slot and version checks still guard SeleniumBase's own discovery.
- Preflight requires the package slot to exist, be executable and resolve to the configured `CHROMEDRIVER_BINARY` according to `samefile`. Browser and driver must report the same **full** version, not just a matching major version. Missing slots, mismatched identities and mismatched versions fail before driver creation rather than triggering fallback provisioning.
- Startup passes that exact `driver_version`, the configured browser binary, task profile and headed options to normal Chrome `Driver()`. After construction it verifies that the returned service executable resolves to the configured driver. `driver_version` alone is not proof of executable identity; both preflight and postconstruction checks matter.
- The factory preserves `LocalBrowserSession(driver, desktop)` and the caller interface. No backend configuration or automatic raw-Selenium retry exists.
- Xvfb/Openbox, desktop geometry/focus, PyAutoGUI/Xlib binding, viewer lifetime, cancellation, profile removal and exclusive lock ownership remain application-managed. Construction, quit and service-stop failures must retain cleanup guarantees.
- Existing tools retain URL policy, write gates, credential/TOTP origin checks, redaction, bounded readiness and single-submit behavior. Legacy `GCW.py` / `ps_lib` migration is out of scope.

The preprovisioned slot and fail-closed checks are the offline-startup design; verify actual no-network worker-thread startup in the Linux image as described below. Do not infer it solely from version arguments or unit mocks.

## Deferred — selective helper adoption

| Existing operation | Proposed treatment |
|---|---|
| Navigation | Keep URL policy checks before/after navigation; compare candidate helper behavior before replacing `get`. |
| Read-only text/element access | Pilot helpers behind the adapter, preserving output bounds and redaction. |
| Readiness polling | Retain the custom loop until equivalent cancellation, coverage, readonly and deadline behavior is demonstrated. |
| Click / fill / hover / keys | Keep the desktop path and live-target checks; no mechanical replacement with SeleniumBase click/type. |
| Credential and TOTP entry | Preserve dedicated tools, exact-origin checks, expiry, no-secret output and no automatic resubmission. |
| DOM / form discovery | Preserve existing scripts and selectors initially. |

The tutorial's `type()` performs waiting, clearing, typing and potentially submitting when text ends in a newline. That is not interchangeable with this project's guarded input sequence. Audit helper retries, implicit navigation waits and exception handling before allowing helpers to perform writes. Every timeout must fit the remaining task budget; a timeout must not be reported as “no input occurred” after a possible write.

## Verification checklist and results

Verification recorded on **2026-10-04**:

- Historical pre-migration Windows Python 3.12.13 baseline: **75 passed** across `test_browser_runtime`, `test_element_readiness` and `test_selenium_tools`.
- Full Windows suite after migration (`python -m pytest tests -q`): **311 passed, 6 skipped in 77.93s**. The six skipped tests require Linux integration opt-in.
- Earlier Windows focused tests: **290 passed**, not the full suite. This comprises 141 across `test_browser_runtime`, `test_desktop_runtime`, `test_element_readiness`, `test_selenium_tools`, `test_desktop_browser_tools`, `test_display_viewer` and `test_agent`, plus 149 credential regressions across `test_login_forms`, `test_totp_tools` and `test_account_tasks`. `uv pip check` reports compatible dependencies.
- Clean Dockerfile build remains **not certified**: the first attempt failed resolving `deb.debian.org`. A second `docker build --load -t posting:seleniumbase-verification .` completed OS package installation but failed downloading the Chrome archive with `curl: (92) HTTP/2 stream 1 was not closed cleanly: INTERNAL_ERROR`. These are build-network failures, not evidence of a browser-launch failure; no clean image or deployment is claimed.
- Alternate image `posting:seleniumbase-smoke` (image ID `sha256:d3e079d9875d336f55768479565978ef54e8bd9ad7101246f992eae9058e1b0c`), based on existing `posting:selenium-verification`, successfully installed the new exact lock and root-owned driver symlink. **5 Linux integration tests passed in 83.53s**, non-root, with Docker `--network none --shm-size=1g`, `RUN_LOCAL_BROWSER_INTEGRATION=1`, and `pytest tests/test_local_browser_integration.py tests/test_display_viewer_integration.py -q -p no:cacheprovider`.
- Linux coverage includes repeated real desktop typing/clicking/scrolling and cleanup; worker-thread startup, cross-thread cancellation and recovery; synthetic agent tools; and real viewer authentication, read-only framebuffer, logout and repeated UI sessions. `sb_install.main` and `SeleniumManager.binary_paths` were patched to reject provisioning and received **zero calls**. Openbox reported 1023×767 for requested 1024×768; the smoke accepts this one-pixel window-manager boundary variance and verifies DPR 1.

- Final combined Linux run on the same alternate image with the same offline command: **6 passed in 100.19s**, including the added constructor-failure regression.
- Additional real Linux constructor-failure regression initially ran alone: **1 passed in 7.64s** on the same offline alternate image. An executable browser fixture reports the exact installed version but exits at launch; the test verifies no driver provisioning, no surviving new ChromeDriver process, profile cleanup, display restoration, lock release and a successful subsequent session.

**Remaining verification:** retry the clean Dockerfile build after build-network recovery and verify actual production egress controls. Preflight error variants retain unit-mock coverage. The successful alternate-image offline smoke does not certify the clean build or production network isolation.

Retain these regression checks when changing the integration:

- [runtime unit tests](../tests/test_browser_runtime.py): sole SeleniumBase factory arguments, exact full-version selection, missing/nonexecutable/wrong package slot, returned-service identity mismatch, startup failure, quit failure, owned service cleanup and lock release.
- [tool tests](../tests/test_selenium_tools.py), [readiness tests](../tests/test_element_readiness.py), [login tests](../tests/test_login_forms.py), [TOTP tests](../tests/test_totp_tools.py): permission parity, stale/covered controls, cancellation, origin restrictions, redaction and single-submit behavior.
- [desktop runtime tests](../tests/test_desktop_runtime.py), [desktop browser tests](../tests/test_desktop_browser_tools.py): focus, typing, scrolling and geometry parity.
- [local integration](../tests/test_local_browser_integration.py): real Linux display, repeated sessions, distinct profiles, actual driver path and ordinary WebDriver behavior. Preserve the existing `navigator.webdriver` and driver-path expectations unless a separately justified contract change is approved.
- [viewer integration](../tests/test_display_viewer_integration.py): browser visible in the same display; disconnect/cleanup on completion and cancellation.
- [agent tests](../tests/test_agent.py), [API tests](../tests/test_api.py), [account task tests](../tests/test_account_tasks.py): unchanged tool schemas, API results and shutdown behavior.
- Retain offline worker-thread startup, cross-thread cancellation/recovery, repeated-task and real constructor-failure checks; cancellation during construction remains a separate verification case.
- Use synthetic pages and mock model replies, not real accounts or external posting actions. Linux integration is explicitly opt-in; Windows unit success alone is insufficient.

**Release acceptance:** no regression in permissions/results; no duplicate submissions; no runtime driver downloads; no surviving owned browser/display processes or profiles; viewer and cancellation remain correct. Compare startup time and image size against baseline; no assumed speed or flakiness improvement.

## Deployment and rollback

1. Build the locked image and complete the synthetic Linux verification checks before production deployment. Record accepted upstream browser flags rather than asserting sandbox/TLS parity.
2. Exercise synthetic browse, authorized form, cancellation and read-only viewer flows; verify root ownership of the package driver slot and non-root runtime access.
3. Drain active tasks and back up task data before deploying the verified image. Preserve one worker/replica and existing display/viewer/container guards.
4. Roll back by deploying the previous image for subsequent tasks, not by selecting a backend. Never automatically retry a failed task through another backend: its writes may already have happened.
5. Keep [README](../README.md) and [.env.example](../.env.example) aligned with the sole backend, pinned dependencies, provisioning contract and accepted security tradeoff.

## Sources and limitations

- [Official migration tutorial](https://seleniumbase.io/examples/migration/raw_selenium/ReadMe/): test-oriented progression and action semantics.
- [Official syntax formats](https://seleniumbase.io/help_docs/syntax_formats/): BaseCase, SB, DriverContext and direct Driver integration.
- [Official repository](https://github.com/seleniumbase/SeleniumBase).
- [Pinned Driver manager source](https://github.com/seleniumbase/SeleniumBase/blob/v4.55.0/seleniumbase/plugins/driver_manager.py): option names and headed-mode handling.

The implementation record describes the integration contract, not a claim that browser sandboxing or TLS validation has been preserved. Deployment acceptance depends on the recorded verification results above; re-audit launcher defaults and driver discovery whenever the SeleniumBase pin changes.
