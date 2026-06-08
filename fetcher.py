"""
Fetcher module for the JioMart Price Tracker.

Responsible for loading the target products, calling the JioMart catalog API
with robust retries and error handling, and normalizing API responses into
the ProductPrice dataclass.
"""

import json
import time
import logging
from dataclasses import dataclass
import requests
import config

# Configure module logger
logger = logging.getLogger(__name__)

@dataclass
class ProductPrice:
    """
    Normalized data container for product pricing info.
    """
    product_name: str
    slug: str
    size: str
    effective_price: float
    marked_price: float
    discount: str
    is_serviceable: bool

def load_products(filepath: str) -> list[dict[str, str]]:
    """
    Loads list of products to track from a JSON file.

    Args:
        filepath (str): Path to products.json.

    Returns:
        list[dict]: List of product dictionaries containing 'slug' and 'size'.
    """
    logger.info(f"Loading products registry from: {filepath}")
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            products = json.load(f)
            if not isinstance(products, list):
                raise ValueError("Products configuration must be a JSON array.")
            return products
    except Exception as e:
        logger.error(f"Failed to load products from registry: {e}")
        raise

def fetch_product_prices(
    products: list[dict[str, str]], 
    max_retries: int = 3, 
    backoff_factor: float = 1.5
) -> list[ProductPrice]:
    """
    Calls the JioMart pricing API with the requested list of products and returns normalized prices.

    Uses an exponential backoff retry mechanism for network/server failures.

    Args:
        products (list[dict]): The products to query, containing 'slug' and 'size'.
        max_retries (int): Maximum number of retry attempts.
        backoff_factor (float): Multiplier for exponential backoff sleep duration.

    Returns:
        list[ProductPrice]: Normalized price data.
    """
    payload = {
        "items": [
            {"slug": p["slug"], "size": p["size"]} for p in products
        ]
    }

    # API request execution with retries
    response = None
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Requesting JioMart API pricing (attempt {attempt}/{max_retries})...")
            resp = requests.post(
                config.jiomart_api_url,
                json=payload,
                headers=config.api_headers,
                timeout=15
            )
            
            # API can return 400 for unserviceable items or missing entries, which still contains structured error items.
            if resp.status_code in (200, 400):
                response = resp
                break
                
            logger.warning(f"JioMart API returned transient status code {resp.status_code} on attempt {attempt}")
            if resp.status_code >= 500:
                time.sleep(backoff_factor ** attempt)
                continue
            else:
                resp.raise_for_status()
        except requests.RequestException as e:
            logger.warning(f"HTTP connection failure on attempt {attempt}: {e}")
            last_exception = e
            if attempt < max_retries:
                time.sleep(backoff_factor ** attempt)
            else:
                raise last_exception

    if response is None:
        raise RuntimeError("Failed to fetch product prices after all retry attempts.")

    # Parse response
    try:
        resp_data = response.json()
    except Exception as e:
        logger.error(f"Failed to decode API JSON response: {e}")
        logger.debug(f"Response content: {response.text}")
        raise ValueError(f"Invalid JSON response from JioMart API: {e}")

    normalized_results: list[ProductPrice] = []
    resp_items = resp_data.get("items", [])

    # Index response items by (slug, size) for faster lookup
    resp_dict: dict[tuple[str, str], dict] = {}
    for item in resp_items:
        s = item.get("slug")
        sz = item.get("size")
        if s:
            resp_dict[(s.lower(), (sz or "").lower())] = item

    # Normalize response data
    for idx, product in enumerate(products):
        slug = product["slug"]
        size = product.get("size", "")
        key = (slug.lower(), size.lower())

        item_data = resp_dict.get(key)
        # Fallback to index-based mapping if slug index fails for any reason
        if not item_data and idx < len(resp_items):
            item_data = resp_items[idx]

        if item_data:
            error_field = item_data.get("error")
            is_serviceable = item_data.get("is_serviceable", True)
            
            if error_field or not is_serviceable or "price" not in item_data:
                # Product is unserviceable or not found
                product_name = item_data.get("product_name") or slug.replace("-", " ").title()
                normalized_results.append(ProductPrice(
                    product_name=product_name,
                    slug=slug,
                    size=size,
                    effective_price=0.0,
                    marked_price=0.0,
                    discount="",
                    is_serviceable=False
                ))
            else:
                # Serviceable product
                price_info = item_data["price"]
                normalized_results.append(ProductPrice(
                    product_name=item_data.get("product_name", slug.replace("-", " ").title()),
                    slug=slug,
                    size=size,
                    effective_price=float(price_info.get("effective", 0.0)),
                    marked_price=float(price_info.get("marked", 0.0)),
                    discount=item_data.get("discount", ""),
                    is_serviceable=True
                ))
        else:
            # Completely missing from response
            normalized_results.append(ProductPrice(
                product_name=slug.replace("-", " ").title(),
                slug=slug,
                size=size,
                effective_price=0.0,
                marked_price=0.0,
                discount="",
                is_serviceable=False
            ))

    return normalized_results

def fetch_all_registered_products() -> list[ProductPrice]:
    """
    Helper function to load products from products.json and fetch their normalized pricing.
    """
    return fetch_product_prices(load_products(config.products_json_path))
