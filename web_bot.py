import os
import requests
from flask import Flask, request
from openai import OpenAI

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

app = Flask(__name__)

def send_message(chat_id, text):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=60
    )

def ask_llm(user_text):
    completion = client.chat.completions.create(
        model="meta/llama-3.3-70b-instruct",
        messages=[
            {"role": "system", "content": "Отвечай только на русском языке."},
            {"role": "user", "content": user_text}
        ],
        temperature=0.6,
        top_p=0.9,
        max_tokens=700,
        stream=False
    )
    return completion.choices[0].message.content.strip()

@app.route("/")
def home():
    return "ok", 200

@app.route("/set_webhook")
def set_webhook():
    if not RENDER_EXTERNAL_URL:
        return "RENDER_EXTERNAL_URL not set", 500

    webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
    r = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
        params={"url": webhook_url},
        timeout=60
    )
    return r.text, 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    message = data.get("message", {})
    chat = message.get("chat", {})
    chat_id = chat.get("id")

    if not chat_id:
        return "ok", 200

    if "text" in message:
        user_text = message["text"]
        answer = ask_llm(user_text)
        send_message(chat_id, answer)

    return "ok", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)