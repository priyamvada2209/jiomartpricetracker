"""
Configuration module for the JioMart Price Tracker.

Loads, validates, and stores environment settings, and dynamically constructs
location-based headers required by the JioMart catalog API.
"""

import os
import json
import logging
from dotenv import load_dotenv

# Configure local module logger
logger = logging.getLogger(__name__)

# Locate and load the .env file
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, ".env")
load_dotenv(env_path)

REQUIRED_ENV_VARS = [
    "JIOMART_API_URL",
    "JIOMART_AUTHORIZATION",
    "LATITUDE",
    "LONGITUDE",
    "POLYGON_ID",
    "CITY",
    "PINCODE",
    "STATE",
    "COUNTRY",
    "COUNTRY_ISO_CODE",
    "DATABASE_URL"
]

# Validate variables fail-fast
missing_vars = []
for var in REQUIRED_ENV_VARS:
    val = os.getenv(var)
    if not val or val.strip() == "":
        missing_vars.append(var)

if missing_vars:
    error_msg = f"Configuration validation failed. Missing or empty environment variables: {', '.join(missing_vars)}"
    logger.critical(error_msg)
    raise ValueError(error_msg)

# Retrieve validated configurations
jiomart_api_url: str = os.environ["JIOMART_API_URL"]
jiomart_authorization: str = os.environ["JIOMART_AUTHORIZATION"]
latitude: str = os.environ["LATITUDE"]
longitude: str = os.environ["LONGITUDE"]
polygon_id: str = os.environ["POLYGON_ID"]
city: str = os.environ["CITY"]
pincode: str = os.environ["PINCODE"]
state: str = os.environ["STATE"]
country: str = os.environ["COUNTRY"]
country_iso_code: str = os.environ["COUNTRY_ISO_CODE"]
database_url: str = os.environ["DATABASE_URL"]

# Dynamically construct headers as compact JSON strings to match original format
x_geolocation: str = json.dumps({
    "latitude": latitude,
    "longitude": longitude,
    "polygon_ids": [polygon_id]
}, separators=(",", ":"))

x_location_detail: str = json.dumps({
    "country": country,
    "country_iso_code": country_iso_code,
    "city": city,
    "pincode": pincode,
    "state": state
}, separators=(",", ":"))

api_headers: dict[str, str] = {
    "authorization": jiomart_authorization,
    "content-type": "application/json",
    "x-geolocation": x_geolocation,
    "x-location-detail": x_location_detail
}

products_json_path: str = os.path.join(current_dir, "products.json")
