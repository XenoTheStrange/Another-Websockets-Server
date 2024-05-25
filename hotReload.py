#!/usr/bin/python3
import asyncio
import logging
import os
import sys
import psutil as yeet
from customLogger import CustomLogger

logger = CustomLogger("hotReload", "info")

def restart_program(filepath, auto=False):
    """Restarts the current program, with file objects and descriptorscleanup"""
    if auto: logger.info("Hot restart triggered")
    else: logger.info("Restart action triggered")
    try:
        p = yeet.Process(os.getpid())
        for handler in p.open_files() + p.connections():
            os.close(handler.fd)
    except Exception as e:
        logging.error(e)
    python=sys.executable
    os.execl(filepath, filepath, "restart")

def read_file(filepath):
    with open(filepath, "r") as file:
        return file.read()

async def handler(filepath):
    while True:
        previous = read_file(filepath)
        await asyncio.sleep(3)
        latest = read_file(filepath)
        if not previous == latest:
            restart_program(filepath, "auto")
