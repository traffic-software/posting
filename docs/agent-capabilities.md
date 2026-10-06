# Desktop fallback, public research and workflow memory

## Browser-scoped mouse and keyboard

The agent already has click, hover, bounded scroll and allowlisted navigation keys. It can also use:

- `double_click_element(selector)`: double-click a freshly inspected safe non-text control.
- `drag_element(source_selector, destination_selector)`: one bounded drag between inspected, simultaneously visible safe controls.
- `select_all_text(selector)`: select text within a verified ordinary editable host, without reading or writing the clipboard.
- `fill_element(selector, value)`: replace ordinary input/textarea text or a real `contenteditable` editing host. False/noneditable elements are recoverable unsupported targets, not secret-field policy failures.

Inspect before acting and observe the result afterwards. Native DOM and PyAutoGUI share the existing write-consent, public-origin, cancellation, focus and readiness guards. Hidden/covered controls are not force-filled. Passwords/OTP use dedicated tools. Generic typing rejects private/sensitive targets and recognized credential autocomplete controls before clearing.

Drag/double-click cannot target editable/private/file/frame controls. Mouse buttons and selection modifiers are released in `finally` blocks; the PyAutoGUI fail-safe remains enabled. No raw global coordinates, arbitrary shortcut chords, shell control, clipboard access or uncertain-write retries are exposed. Existing masked screenshot fallback remains a fresh, one-use, browser-viewport **click-only** tool; it cannot click or type into masked editors. Unicode ordinary text uses Selenium key delivery. Generic fill currently accepts 1–2,000 printable characters, not multiline/control-character input.

## Cloudflare `web-search`

Enable this explicitly in server configuration:

```dotenv
ENABLE_WEB_SEARCH=true
CLOUDFLARE_ACCOUNT_ID=your-32-character-hex-account-id
CLOUDFLARE_API_TOKEN=your-server-held-token
CLOUDFLARE_WEB_SEARCH_GATEWAY=default
CLOUDFLARE_WEB_SEARCH_PROVIDER=ceramic
WEB_SEARCH_TIMEOUT_SECONDS=10
MAX_WEB_SEARCH_CALLS=3
```

The provider may be `ceramic`, `exa` or `linkup`. Cloudflare requires a configured AI Gateway and gateway credits or a provider credential, plus token permissions described in its usage guide. The tool posts to `/client/v4/accounts/{account_id}/ai/websearch/` with `query`, `provider`, `limit`, and `options.gateway.id`.

Use research when the task is unfamiliar, the next safe action is unclear, or a recoverable failure remains unexplained after fresh browser inspection. Send a short generic documentation query—not the full task prompt or account content. The optional `reason` stays local. Queries are capped at 1,024 characters and results at 10 (default 5); responses and snippets are bounded. Failed requests consume the per-task request cap. No retries or automatic browser navigation occur. Missing configuration/provider failures return recoverable tool errors.

Known task/server secrets, credential-like assignments, email addresses and long token-like strings are rejected. These checks are defensive heuristics, not a guarantee of detecting every kind of private information; the agent must still keep private content out of queries. Results are untrusted reference data, not instructions or permission to bypass browser policy. Result URLs are not fetched or DNS-resolved by this tool; normal navigation checks still apply if the agent later opens a result.

Requests are recorded through Cloudflare AI Gateway according to its documentation. Review the gateway's **Settings → Logs** option before enabling search on sensitive deployments. Disabling gateway logging does not establish a third-party search provider's retention policy. Synchronous HTTP work uses short timeouts and deadline checks, but cancellation cannot immediately interrupt a socket operation already in progress.

## Same-profile verified workflow hints

```dotenv
ENABLE_WORKFLOW_MEMORY=true
WORKFLOW_MEMORY_LIMIT=100
WORKFLOW_MEMORY_DAYS=90
```

Workflows live in a separate `workflows` table in the existing task SQLite database, so they survive ordinary server restarts. Retrieval is limited to the **same persistent browser profile and exact public HTTPS origin**. Matching uses local task-intent words, not an external embeddings service. Per-profile retention defaults to 100 workflows/90 days. Tasks without a persistent profile cannot create reusable account workflows.

Tools:

- `lookup_workflow(origin, intent)` returns up to three sanitized advisory flows; no browser actions are replayed.
- `verify_workflow_outcome()` checks caller-defined visible outcome criteria against the fresh page.
- `remember_successful_workflow(intent, origin, steps, prerequisites)` stages a bounded declarative candidate. It does **not** save it immediately.

Saving needs all of the following:

1. Workflow memory enabled and a persistent `browser_profile_id`.
2. Caller-supplied `workflow_success_criteria`, not criteria invented by the agent.
3. A staged semantic candidate without credentials, screenshots, scripts, raw prompts or transient selectors.
4. All criteria freshly matched at terminal completion on the candidate's HTTPS origin.
5. The task's `COMPLETED` record durably written before best-effort workflow persistence.

Example addition to an authenticated `/run-task` request:

```json
{
  "prompt": "Follow the authorized video workflow and verify the completed result.",
  "allow_write_actions": true,
  "browser_profile_id": "replace-with-existing-32-hex-profile-id",
  "workflow_success_criteria": [
    {
      "origin": "https://your-authorized-site.example",
      "selector": "#job-status",
      "expected_text": "Generation complete"
    }
  ]
}
```

Use actual stable visible outcome targets for the site. Up to three criteria are supported; all must match on the same origin. Verification reads bounded visible non-private, non-editable DOM text and requires the expected text; it does not read input values or execute supplied JavaScript. Store criteria without private values. Observing a user-selected confirmation is evidence of that visible state—not a general guarantee about every external side effect, artifact or task substep. Choose criteria that meaningfully represent the requested result.

A normal `COMPLETED` task, model claim or successful click receipt alone never creates a verified-success workflow. Without supported criteria, tasks execute and report normally but no verified flow is saved. Failed/cancelled/interrupted/unverified attempts are not promoted; memory failure does not change a completed task's public result. The existing `result.output` and task-status semantics remain unchanged.

At task start the agent receives a bounded set of matching hints when an exact HTTPS origin is supplied in its goal/criteria, and can look up additional hints while working. Historical hints remain untrusted: re-inspect current controls and never reuse stale selectors, coordinates, screenshot IDs or account assumptions. After a changed workflow completes and verifies, a staged same-intent candidate updates the existing entry.

## Offline validation

```bash
python -m pytest tests/test_web_research.py tests/test_workflow_memory.py tests/test_agent_capabilities.py -q
```

`tests/test_capability_browser_integration.py` is opt-in with `RUN_LOCAL_BROWSER_INTEGRATION=1` in a configured Linux/Xvfb environment. It uses a synthetic local page, not external accounts or paid search calls.

References:

- https://pyautogui.readthedocs.io/en/latest/
- https://developers.cloudflare.com/web-search/how-to-use/
- https://developers.cloudflare.com/ai-gateway/observability/logging/
