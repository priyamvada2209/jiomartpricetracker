"""
Scheduler module for the JioMart Price Tracker.

Defines the scheduled job that pulls prices, prints the required text
summary, and persists records in the SQL database daily at 6:00 AM.
"""

import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from fetcher import fetch_all_registered_products, ProductPrice
from database import get_db
from models import PriceHistory
import notifier
from sqlalchemy import desc

# Configure module logger
logger = logging.getLogger(__name__)

def format_summary(prices: list[ProductPrice]) -> str:
    """
    Formats product pricing records into a user-facing text summary.

    Args:
        prices (list[ProductPrice]): List of normalized product prices.

    Returns:
        str: Formatted multi-line text summary.
    """
    lines = ["JioMart Daily Prices"]
    for p in prices:
        lines.append(p.product_name)
        if p.is_serviceable:
            # Represent whole numbers without decimals (e.g. 130 instead of 130.0)
            val = int(p.effective_price) if p.effective_price.is_integer() else p.effective_price
            mrp = int(p.marked_price) if p.marked_price.is_integer() else p.marked_price
            lines.append(f"₹{val} (MRP ₹{mrp})")
        else:
            lines.append("Not Serviceable")
    return "\n".join(lines)

def run_price_tracker_job() -> None:
    """
    Main execution task. Fetches prices, displays summary, and logs history in the SQL database.
    Sends notifications via Telegram.
    """
    logger.info("Executing JioMart price check job...")
    try:
        prices = fetch_all_registered_products()
        
        price_drops = []
        
        # Save records in SQLite/SQL database and check for price drops
        with get_db() as session:
            for p in prices:
                if p.is_serviceable:
                    # Find yesterday's (or latest previous) price
                    last_record = session.query(PriceHistory).filter_by(product_slug=p.slug).order_by(desc(PriceHistory.fetched_at)).first()
                    
                    if last_record and last_record.price is not None:
                        if p.effective_price < last_record.price:
                            val = int(p.effective_price) if p.effective_price.is_integer() else p.effective_price
                            old_val = int(last_record.price) if last_record.price.is_integer() else last_record.price
                            diff = old_val - val
                            price_drops.append((p.product_name, old_val, val, diff))
                
                # If product is unserviceable, store price as None (NULL in database)
                db_record = PriceHistory(
                    product_slug=p.slug,
                    product_name=p.product_name,
                    price=p.effective_price if p.is_serviceable else None,
                    fetched_at=datetime.now()
                )
                session.add(db_record)
            
            # Context manager auto-commits on success
            logger.info("Successfully persisted fetched prices to database.")
            
        # Build and output formatted text summary
        summary = format_summary(prices)
        print(summary)
        
        # Send Telegram Notification
        if price_drops:
            lines = ["Price Drop Alert"]
            for drop in price_drops:
                lines.append(drop[0])
                lines.append(f"Yesterday: ₹{drop[1]}")
                lines.append(f"Today: ₹{drop[2]}")
                lines.append(f"Difference: -₹{drop[3]}")
            
            notification_text = "\n".join(lines)
        else:
            notification_text = summary
            
        try:
            notifier.send_message(notification_text)
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            
    except Exception as e:
        logger.error(f"Error during job execution: {e}", exc_info=True)

def start_scheduler() -> None:
    """
    Sets up and starts the blocking daily schedule runner.
    """
    scheduler = BlockingScheduler()
    # Trigger daily at 6:00 AM
    scheduler.add_job(
        run_price_tracker_job, 
        "cron", 
        hour=6, 
        minute=0, 
        id="jiomart_daily_fetch_job"
    )
    logger.info("APScheduler daily job registered for 6:00 AM.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("APScheduler stopped by system/user request.")
