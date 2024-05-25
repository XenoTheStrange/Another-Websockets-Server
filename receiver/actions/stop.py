#!/usr/bin/python3
import sys

sys.path.append("/hdd/desktop/delegator/server/receiver/")
from utils import CustomLogger

logger = CustomLogger("stop.py", "info")

async def main(*args):
    obj = args[0]
    username = args[1]
    websocket = args[2]
    logger.info(f"[INFO]: Server kill received from {username}")
    await websocket.send("[INFO]: Server will stop.")
    await websocket.close()
    sys.exit()
