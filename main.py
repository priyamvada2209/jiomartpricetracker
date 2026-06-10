"""
Main entrypoint module for the JioMart Price Tracker application.
"""

import os
import sys
import logging

# Ensure standard output can encode and print Unicode characters like '₹' on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure the module's directory is placed at the top of the sys.path list
# to support smooth flat local imports regardless of invocation path.
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import config
import database
import scheduler

# Configure logging to write to both stdout and a rolling log file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(current_dir, "price_tracker.log"), encoding="utf-8")
    ]
)

logger = logging.getLogger(__name__)

def main() -> None:
    """
    Sets up the database tables, executes the initial price check, and starts the scheduler loop.
    """
    logger.info("Starting JioMart Price Tracker...")
    
    # Initialize SQL database tables
    try:
        database.init_db()
        logger.info("SQL database schema initialized successfully.")
    except Exception as e:
        logger.critical(f"Failed to initialize database: {e}", exc_info=True)
        sys.exit(1)

    # Run the tracking job once on startup immediately to verify functionality
    logger.info("Executing initial startup price tracker run...")
    scheduler.run_price_tracker_job()

    # Start daily scheduling
    # logger.info("Initializing daily scheduler loop...")
    # scheduler.start_scheduler()

if __name__ == "__main__":
    main()
