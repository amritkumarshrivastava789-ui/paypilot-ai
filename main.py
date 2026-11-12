import os
import base64
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="PayPilot AI", description="AI-assisted payment guidance with PayPal Sandbox checkout.")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

class AskRequest(BaseModel):
    message: str

class OrderRequest(BaseModel):
    amount: str = "10.00"
    currency: str = "USD"

def paypal_config():
    client_id = os.getenv("PAYPAL_CLIENT_ID", "").strip()
    secret = os.getenv("PAYPAL_CLIENT_SECRET", "").strip()
    mode = os.getenv("PAYPAL_MODE", "sandbox").lower()
    if not client_id or not secret:
        raise HTTPException(status_code=503, detail="PayPal Sandbox is not configured. Add PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET to .env.")
    if mode != "live":
        return client_id, secret, "https://api-m.sandbox.paypal.com"
    return client_id, secret, "https://api-m.paypal.com"

async def paypal_token(client_id: str, secret: str, base_url: str):
    auth = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{base_url}/v1/oauth2/token",
            headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials"},
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Could not authenticate with PayPal. Check your Sandbox credentials.")
    return response.json()["access_token"]

@app.get("/")
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")

@app.get("/api/config")
def config():
    return {
        "paypal_client_id": os.getenv("PAYPAL_CLIENT_ID", ""),
        "paypal_mode": os.getenv("PAYPAL_MODE", "sandbox"),
        "paypal_ready": bool(os.getenv("PAYPAL_CLIENT_ID") and os.getenv("PAYPAL_CLIENT_SECRET")),
    }

@app.post("/api/ask")
async def ask(req: AskRequest):
    prompt = req.message.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Please enter a question.")
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
                contents=(
                    "You are PayPilot, a concise payment guidance assistant. "
                    "Explain payment concepts and checkout safety. Never claim a payment succeeded "
                    "unless the PayPal capture endpoint confirms it. Do not ask for card numbers, "
                    "passwords, or one-time passcodes. This is not financial or legal advice.\n\n"
                    f"User: {prompt}"
                ),
            )
            return {"answer": response.text, "mode": "Gemini AI"}
        except Exception as e:
            print("Gemini API error:", repr(e), flush=True)
            lower = prompt.lower()
            if any(word in lower for word in ["safe", "secure", "scam", "fraud"]):
                answer = ("Use the official PayPal checkout window, verify the merchant and amount before approving, "
                          "and never share your password or one-time code. This demo cannot independently verify a seller.")
            elif any(word in lower for word in ["refund", "cancel", "return"]):
                answer = ("Check the seller's return policy and the transaction details in your PayPal account. "
                          "If a payment has already been made, use PayPal's official Resolution Center for eligible disputes.")
            elif any(word in lower for word in ["fee", "charge", "currency", "conversion"]):
                answer = ("Payment fees and currency-conversion rates depend on the transaction, account, and country. "
                          "Review the final amount shown by PayPal before confirming.")
            else:
                answer = ("I can help explain checkout steps, payment safety, refunds, and currency or fee questions. "
                          "For personalized AI answers, add a Gemini API key to your .env file.")
            return {"answer": answer, "mode": "Built-in demo assistant"}

@app.post("/api/paypal/create-order")
async def create_order(req: OrderRequest):
    try:
        amount = f"{float(req.amount):.2f}"
    except ValueError:
        raise HTTPException(status_code=400, detail="Amount must be a valid number.")
    if float(amount) <= 0:
        raise HTTPException(status_code=400, detail="Amount must be greater than zero.")
    if req.currency.upper() not in {"USD", "EUR", "GBP"}:
        raise HTTPException(status_code=400, detail="Demo supports USD, EUR, and GBP.")
    client_id, secret, base_url = paypal_config()
    token = await paypal_token(client_id, secret, base_url)
    payload = {
        "intent": "CAPTURE",
        "purchase_units": [{"amount": {"currency_code": req.currency.upper(), "value": amount},
                            "description": "PayPilot AI demo checkout"}],
        "application_context": {"brand_name": "PayPilot AI", "user_action": "PAY_NOW",
                                "shipping_preference": "NO_SHIPPING"}
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f"{base_url}/v2/checkout/orders",
                                     headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                                     json=payload)
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="PayPal could not create the order. Check your Sandbox app.")
    data = response.json()
    return {"id": data["id"], "status": data["status"]}

class CaptureRequest(BaseModel):
    order_id: str

@app.post("/api/paypal/capture-order")
async def capture_order(req: CaptureRequest):
    client_id, secret, base_url = paypal_config()
    token = await paypal_token(client_id, secret, base_url)
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(
            f"{base_url}/v2/checkout/orders/{req.order_id}/capture",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="PayPal did not capture this order.")
    data = response.json()
    return {"id": data.get("id"), "status": data.get("status"), "details": data}
