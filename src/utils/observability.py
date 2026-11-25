import logging
import os
from datetime import datetime
from src.config import config

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_LEVEL = config.get("LOG_LEVEL", "INFO").upper()

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)


def log_info(message: str) -> None:
    logging.info(message)


def log_error(message: str) -> None:
    logging.error(message)


def log_performance_metrics(metrics: dict) -> None:
    logging.info("Performance Metrics: %s", metrics)


def log_exception(exc: Exception) -> None:
    logging.error("Exception occurred: %s", exc, exc_info=True)


def log_request(request_info: dict) -> None:
    logging.info("Request Info: %s", request_info)


def log_response(response_info: dict) -> None:
    logging.info("Response Info: %s", response_info)
