"""
JioMart price fetcher.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass

import requests

from . import config

logger = logging.getLogger(__name__)


@dataclass
class ProductPrice:
    product_name: str
    slug: str
    size: str
    effective_price: float
    marked_price: float
    discount: str
    is_serviceable: bool


def load_products(filepath: str) -> list[dict[str, str]]:
    logger.info("Loading products registry from: %s", filepath)
    with open(filepath, "r", encoding="utf-8") as file_handle:
        products = json.load(file_handle)
    if not isinstance(products, list):
        raise ValueError("Products configuration must be a JSON array.")
    return products


def fetch_product_prices(
    products: list[dict[str, str]],
    max_retries: int = 3,
    backoff_factor: float = 1.5,
) -> list[ProductPrice]:
    payload = {"items": [{"slug": product["slug"], "size": product["size"]} for product in products]}

    response = None
    last_exception: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info("Requesting JioMart API pricing (attempt %s/%s)...", attempt, max_retries)
            response_candidate = requests.post(
                config.jiomart_api_url,
                json=payload,
                headers=config.api_headers,
                timeout=15,
            )

            if response_candidate.status_code in (200, 400):
                response = response_candidate
                break

            logger.warning(
                "JioMart API returned transient status code %s on attempt %s",
                response_candidate.status_code,
                attempt,
            )
            if response_candidate.status_code >= 500:
                time.sleep(backoff_factor**attempt)
                continue
            response_candidate.raise_for_status()
        except requests.RequestException as exc:
            logger.warning("HTTP connection failure on attempt %s: %s", attempt, exc)
            last_exception = exc
            if attempt < max_retries:
                time.sleep(backoff_factor**attempt)
            else:
                raise

    if response is None:
        raise RuntimeError("Failed to fetch product prices after all retry attempts.") from last_exception

    try:
        resp_data = response.json()
    except Exception as exc:
        logger.error("Failed to decode API JSON response: %s", exc)
        logger.debug("Response content: %s", response.text)
        raise ValueError(f"Invalid JSON response from JioMart API: {exc}") from exc

    normalized_results: list[ProductPrice] = []
    resp_items = resp_data.get("items", [])
    resp_dict: dict[tuple[str, str], dict] = {}

    for item in resp_items:
        slug = item.get("slug")
        size = item.get("size")
        if slug:
            resp_dict[(slug.lower(), (size or "").lower())] = item

    for index, product in enumerate(products):
        slug = product["slug"]
        size = product.get("size", "")
        key = (slug.lower(), size.lower())
        item_data = resp_dict.get(key)

        if not item_data and index < len(resp_items):
            item_data = resp_items[index]

        if item_data:
            error_field = item_data.get("error")
            is_serviceable = item_data.get("is_serviceable", True)

            if error_field or not is_serviceable or "price" not in item_data:
                normalized_results.append(
                    ProductPrice(
                        product_name=item_data.get("product_name") or slug.replace("-", " ").title(),
                        slug=slug,
                        size=size,
                        effective_price=0.0,
                        marked_price=0.0,
                        discount="",
                        is_serviceable=False,
                    )
                )
            else:
                price_info = item_data["price"]
                normalized_results.append(
                    ProductPrice(
                        product_name=item_data.get("product_name", slug.replace("-", " ").title()),
                        slug=slug,
                        size=size,
                        effective_price=float(price_info.get("effective", 0.0)),
                        marked_price=float(price_info.get("marked", 0.0)),
                        discount=item_data.get("discount", ""),
                        is_serviceable=True,
                    )
                )
        else:
            normalized_results.append(
                ProductPrice(
                    product_name=slug.replace("-", " ").title(),
                    slug=slug,
                    size=size,
                    effective_price=0.0,
                    marked_price=0.0,
                    discount="",
                    is_serviceable=False,
                )
            )

    return normalized_results


def fetch_all_registered_products() -> list[ProductPrice]:
    return fetch_product_prices(load_products(config.products_json_path))

