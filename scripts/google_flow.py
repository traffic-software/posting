import requests
import json

# API endpoint and headers
url = "http://127.0.0.1:8001/run-task"
headers = {
    "Authorization": "Bearer hjfujut-jk-u7u",
    "Content-Type": "application/json"
}

# Task prompt description
prompt_text = (
    "Open https://labs.google/fx/tools/flow with the selected existing signed-in browser profile. "
    "Stop and report if sign-in, CAPTCHA, or manual verification is needed; never bypass it. "
    "Use DOM inspection to verify controls and state. If screenshots are unavailable, continue only "
    "when DOM tools provide verification. Never bypass visual safety checks, guess coordinates, or "
    "repeatedly click header links. Use bounded waits within the task deadline throughout. "
    "Create project: Inspect for the actual New project control at most twice, with a bounded wait "
    "between inspections. If unavailable, stop and report the blocker. Click the verified control "
    "exactly once. Wait up to 30 seconds within the remaining deadline for the workspace. Inspect "
    "it at most twice with a bounded wait between inspections; never re-click New project if loading "
    "or uncertain. Locate a verified input, textarea, or contenteditable prompt editor; stop if absent. "
    "Configure: Select video/text-to-video mode if needed using a verified control. Enter exactly once: "
    "\"A beautiful Makoto Shinkai style anime illustration of a boy walking along a countryside pathway "
    "next to a blooming cherry blossom tree. Bright blue sky with fluffy white clouds, soft pastel colors, "
    "emotional atmosphere, highly detailed animation style.\" Verify the editor contains this prompt. "
    "Set duration to 8 seconds if a verified control supports it; otherwise keep the existing duration "
    "and report the limitation. Select one output if supported. Do not buy credits, subscribe, upgrade, "
    "change account settings, or publish/share publicly. Stop if payment or an upgrade is required. "
    "Generate: Verify the actual submission control and submit exactly one request. Observe status "
    "with bounded waits and fresh DOM inspections within the deadline. Never resubmit a slow, pending, "
    "or uncertain request. Completion requires a completed video result associated with this request; "
    "a receipt, spinner, thumbnail, or elapsed time is not proof. On failure, blockage, or timeout, "
    "report the observed state without claiming success or submitting again. "
    "Download only after verified completion: Inspect the video's download control and use dedicated "
    "file-download tools to save the actual video as a task output artifact, not a thumbnail, preview "
    "image, page, or unrelated file. For an observed direct file link, prefer download_link to read "
    "the live URL server-side without copying signed URLs into model arguments or final text. For "
    "authenticated browser/Blob downloads, use download_from_element on the verified control; it "
    "must arm and click exactly once, with no separate click beforehand. If pending, call "
    "wait_for_download with the returned download_id; never re-click or restart an uncertain transfer. "
    "If a menu appears, inspect it and select the verified video-download option without repeatedly "
    "clicking the original control. Dedicated tools must confirm a READY output artifact; browser "
    "notifications or stable file size alone are insufficient. Never execute, install, or extract downloads. "
    "Final: Report verified generation/download success and any duration limitation, or the precise "
    "blocker and what remains unverified. Never claim a download without a READY artifact. Do not "
    "return or invent source/signed/Blob URLs, filesystem paths, or project/page URLs. The server "
    "supplies the expiring link separately in artifacts[].download_url in the task-status response."
)

# JSON payload data
payload = {
    "browser_profile_id": "6ac1a627c66f092b8ee3d79ea55a6a39",
    "allow_write_actions": True,
    "allow_file_downloads": True,
    "prompt": prompt_text
}

# Sending the POST request
try:
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    # Print responses
    print(f"Status Code: {response.status_code}")
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2))
except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")
