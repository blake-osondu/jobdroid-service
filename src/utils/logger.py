import logging
import sys
from datetime import datetime
from pathlib import Path
import json
from typing import Any, Dict
import traceback

class CustomFormatter(logging.Formatter):
    """Custom formatter with color coding and structured output"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # CYAN
        'INFO': '\033[32m',     # GREEN
        'WARNING': '\033[33m',  # YELLOW
        'ERROR': '\033[31m',    # RED
        'CRITICAL': '\033[41m', # RED BACKGROUND
        'RESET': '\033[0m'      # RESET
    }

    def format(self, record: logging.LogRecord) -> str:
        # Add color to log level
        levelname = record.levelname
        if levelname in self.COLORS:
            colored_levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            record.levelname = colored_levelname

        # Add timestamp
        record.timestamp = datetime.utcnow().isoformat()

        # Format exception info if present
        if record.exc_info:
            record.exc_text = ''.join(traceback.format_exception(*record.exc_info))

        return super().format(record)

class JobBotLogger:
    """Custom logger for the job application bot"""
    
    def __init__(self, name: str, log_dir: str = "logs"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Create logs directory if it doesn't exist
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        
        # File handler for all logs
        file_handler = logging.FileHandler(
            log_path / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(timestamp)s [%(levelname)s] %(name)s: %(message)s'
        ))
        
        # File handler for errors only
        error_handler = logging.FileHandler(
            log_path / f"{name}_errors_{datetime.now().strftime('%Y%m%d')}.log"
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(
            '%(timestamp)s [%(levelname)s] %(name)s: %(message)s\n%(exc_text)s'
        ))
        
        # Console handler with color formatting
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(CustomFormatter(
            '%(timestamp)s [%(levelname)s] %(name)s: %(message)s'
        ))
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)
    
    def log_automation_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log automation events with structured data"""
        try:
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event_type": event_type,
                "data": data
            }
            self.logger.info(json.dumps(log_entry))
        except Exception as e:
            self.logger.error(f"Failed to log automation event: {e}")
    
    def log_error(self, error: Exception, context: Dict[str, Any] = None) -> None:
        """Log errors with context"""
        try:
            error_data = {
                "error_type": type(error).__name__,
                "error_message": str(error),
                "traceback": traceback.format_exc(),
                "context": context or {}
            }
            self.logger.error(json.dumps(error_data))
        except Exception as e:
            self.logger.error(f"Failed to log error: {e}")
