import logging
import logging.handlers
from pathlib import Path


def setup_logging(level=logging.INFO, max_bytes=5 * 1024 * 1024, backup_count=5):
    """Configure logging for the application.

    - Uses a rotating file handler to avoid unbounded growth.
    - Returns a logger instance named `yt_downloader`.
    """
    log_dir = Path.home() / ".yt_downloader" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "app.log"

    logger = logging.getLogger("yt_downloader")
    logger.setLevel(level)

    fmt = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if logger.handlers:
        # Update existing handlers with new settings
        for h in logger.handlers[:]:
            h.setLevel(level)
            if isinstance(h, logging.handlers.RotatingFileHandler):
                logger.removeHandler(h)
                h.close()
            elif isinstance(h, logging.StreamHandler) and not isinstance(h, logging.handlers.RotatingFileHandler):
                h.setFormatter(fmt)
        # Recreate file handler with new max_bytes/backup_count
        rfh = logging.handlers.RotatingFileHandler(str(log_file), maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
        rfh.setFormatter(fmt)
        logger.addHandler(rfh)
        return logger

    # Rotating file handler
    rfh = logging.handlers.RotatingFileHandler(str(log_file), maxBytes=max_bytes, backupCount=backup_count, encoding='utf-8')
    rfh.setFormatter(fmt)
    logger.addHandler(rfh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    logger.info("Logging initialized.")
    return logger
