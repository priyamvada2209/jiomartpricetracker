"""
Configuration loading for the JioMart Price Tracker bot.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)

bot_token = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN")
webhook_url = os.getenv("WEBHOOK_URL")
database_url = os.getenv("DATABASE_URL")
jiomart_api_url = os.getenv("JIOMART_API_URL")
jiomart_authorization = os.getenv("JIOMART_AUTHORIZATION")
latitude = os.getenv("LATITUDE")
longitude = os.getenv("LONGITUDE")
polygon_id = os.getenv("POLYGON_ID")
city = os.getenv("CITY")
pincode = os.getenv("PINCODE")
state = os.getenv("STATE")
country = os.getenv("COUNTRY")
country_iso_code = os.getenv("COUNTRY_ISO_CODE")

required_env_vars = {
    "DATABASE_URL": database_url,
    "JIOMART_API_URL": jiomart_api_url,
    "JIOMART_AUTHORIZATION": jiomart_authorization,
    "LATITUDE": latitude,
    "LONGITUDE": longitude,
    "POLYGON_ID": polygon_id,
    "CITY": city,
    "PINCODE": pincode,
    "STATE": state,
    "COUNTRY": country,
    "COUNTRY_ISO_CODE": country_iso_code,
}

missing_vars = [name for name, value in required_env_vars.items() if not value or not value.strip()]
if missing_vars:
    error_message = (
        "Configuration validation failed. Missing or empty environment "
        f"variables: {', '.join(missing_vars)}"
    )
    logger.critical(error_message)
    raise ValueError(error_message)

x_geolocation = json.dumps(
    {
        "latitude": latitude,
        "longitude": longitude,
        "polygon_ids": [polygon_id],
    },
    separators=(",", ":"),
)

x_location_detail = json.dumps(
    {
        "country": country,
        "country_iso_code": country_iso_code,
        "city": city,
        "pincode": pincode,
        "state": state,
    },
    separators=(",", ":"),
)

api_headers: dict[str, str] = {
    "authorization": jiomart_authorization,
    "content-type": "application/json",
    "x-geolocation": x_geolocation,
    "x-location-detail": x_location_detail,
}

products_json_path = str(PROJECT_ROOT / "products.json")
log_file_path = str(PROJECT_ROOT / "price_tracker.log")
