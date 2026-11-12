# PayPilot AI — Smart Payment Companion

A hackathon prototype with:
- A payment Q&A assistant (built-in responses; optional Gemini API integration).
- PayPal Sandbox order creation and capture endpoints.
- A responsive browser UI with a clear prototype/safety notice.

## Requirements
- Python 3.10+
- Optional: PayPal Developer Sandbox REST app credentials
- Optional: Gemini API key

## Run locally (Windows PowerShell)
```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn main:app --reload
```
Open http://127.0.0.1:8000

## Enable Gemini responses
Add your key to `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key
```
Restart the server. If the API call fails or no key is configured, the built-in demo assistant responds.

## Enable PayPal Sandbox checkout
1. Sign in at https://developer.paypal.com/
2. Create a Sandbox REST app and copy its **Sandbox** Client ID and Secret.
3. Put them in `.env`:
```env
PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=your_sandbox_client_id
PAYPAL_CLIENT_SECRET=your_sandbox_secret
```
4. Restart the server. Use a PayPal Sandbox personal test account in checkout.

Do not use live credentials for a hackathon demo. Never commit `.env` or expose the Secret in frontend code. The backend keeps the secret server-side.

## API
- `GET /api/config`
- `POST /api/ask` with `{"message":"How do I check if a payment is safe?"}`
- `POST /api/paypal/create-order` with `{"amount":"10.00","currency":"USD"}`
- `POST /api/paypal/capture-order` with `{"order_id":"..."}`

## Important honesty note for the submission
This is starter code, not proof of a completed deployment. Gemini and PayPal Sandbox only work after you add valid credentials and test the flows. Do not claim a payment was processed unless PayPal returns `COMPLETED`. Add screenshots/video only after running and testing the app.
