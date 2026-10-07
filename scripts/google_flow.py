import requests
import json

# API endpoint and headers
url = "http://127.0.0.1:8001/run-task"
headers = {
    "Authorization": "Bearer hjfujut-jk-u7u",
    "Content-Type": "application/json"
}
video_prompt = (
    "A young boy working on a laptop, smiling and looking directly at the camera. "
    "He is wearing a red t-shirt, with a laptop placed next to his bag. "
    "The background features a lush park filled with vibrant green trees and blooming flowers. "
    "Captured during the daytime in high resolution with soft, natural sunlight and realistic lighting."
)

# Task prompt description
prompt_text = (
    "Create and download one video in Google Flow:\n"
    "1. Open https://labs.google/fx/tools/flow and create a fresh new project. "
    "Do not reuse an existing project or delete anything.\n"
    "2. Select video generation and set the output count to x1.\n"
    f"3. Enter this exact prompt: \"{video_prompt}\". Submit generation exactly once.\n"
    "4. After submission, wait one minute using supported browser capabilities within the task deadline. "
    "Then find the newly appeared video thumbnail/card belonging to this request, not an arbitrary new element. "
    "If it is still processing, continue bounded observation until ready; elapsed time alone does not prove completion.\n"
    """5. Click the center of that video's thumbnail once to open its editor. জেনারেট হইছে কনফার্ম হতে video element deo check aria-label="Generated video" """
    "The editor URL should have the form https://flow.google.com/project/<project-id>/edit/<video-id>. "
    "Use the actual video, not invented IDs. If already in its editor, do not reopen it.\n"
    "6. In the video editor's toolbar/menu bar, find the Download icon or button. "
    "Open its menu if necessary and choose the actual video-download option, keeping the default variant.\n"
    "7. Prepare browser download collection before the transfer-starting click. "
    "Start the download exactly once and let the download tools collect the completed video. "
    "Wait for the same transfer to finish; never click again because it is slow or pending.\n"
    "8. Report success only after the actual video is saved as a verified output artifact. "
    "The server supplies its download link separately. If blocked, report what completed and what remains unverified.\n"
    "Do not generate again, purchase credits, change account settings, bypass verification, guess click targets, "
    "or execute downloaded files. Choose the available browser tools yourself to carry out these steps safely.\n"
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
