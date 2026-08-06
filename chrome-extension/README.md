# JobPilot Chrome Extension

Load unpacked in Chrome:

1. Open `chrome://extensions`
2. Enable Developer mode
3. Load unpacked → select `chrome-extension/`
4. Open the popup, paste your API base + JWT access token
5. Click **Send job** on any job page → `POST /api/v1/jobs/ingest`
