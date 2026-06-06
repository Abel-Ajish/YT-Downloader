import logging
import os
from pathlib import Path

def setup_logging():
    """Configure logging for the application."""
    log_dir = Path.home() / ".yt_downloader" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "app.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger("yt_downloader")
    logger.info("Logging initialized.")
    return logger
