#!/usr/bin/python3
import logging
import sys
import os
from typing import Any

class CustomLogger:
    def __init__(self, name: str, logLevel):
        self._name = name
        match logLevel.lower():
            case "debug":
                level = logging.DEBUG
            case "info":
                level = logging.INFO
            case "warn":
                level = logging.WARN
            case "error":
                level = logging.ERROR
            case "critical":
                level = logging.CRITICAL
            case "fatal":
                level = logging.FATAL
            case _:
                level = logging.DEBUG
        logging.basicConfig(stream=sys.stdout, level=level)
        # Create a logger
        self._logger = logging.getLogger(self._name)
        # Add file handler
        current_dir = os.path.dirname(__file__)
        if not os.path.exists(os.path.join(current_dir, 'logs')):
            os.mkdir(os.path.join(current_dir, 'logs'))
        log_filename = os.path.join(current_dir, f'logs/{self._name}.log')
        file_handler = logging.FileHandler(log_filename, mode='a')
        file_handler.setLevel(logging.DEBUG)
        self._logger.addHandler(file_handler)
    def debug(self, message: Any, data=""): return self._logger.debug(f'{message}')
    def info(self, message: Any, data=""): return self._logger.info(f'{message}')
    def warning(self, message: Any, data=""): return self._logger.warning(f'{message}')
    def error(self, message: Any, data=""): return self._logger.error(f'{message}')
    def critical(self, message: Any, data=""): return self._logger.critical(f'{message}')
