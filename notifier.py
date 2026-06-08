import os
import requests
import logging

logger = logging.getLogger(__name__)

def send_message(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        raise ValueError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing from environment variables")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    
    response = requests.post(url, json=payload, timeout=30)
    
    if response.status_code != 200:
        logger.error(f"Telegram API request failed with status code {response.status_code}: {response.text}")
        raise Exception(f"Telegram API returned non-200 status code: {response.status_code}")
        
    data = response.json()
    if not data.get("ok"):
        logger.error(f"Telegram API request failed: {data}")
        raise Exception('Telegram returned {"ok": false}')
        
    logger.info("Successfully sent Telegram notification.")
