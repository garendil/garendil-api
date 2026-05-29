import json
import logging
from datetime import datetime


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra_data"):
            data["context"] = record.extra_data
        return json.dumps(data)


def configure_logging() -> logging.Logger:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    return root
