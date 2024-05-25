#!/usr/bin/python3

import sys

sys.path.append("/hdd/desktop/delegator/server/receiver/")
from utils import restart_program

async def main(*args):
    websocket = args[2]
    await websocket.send("[INFO]: Server will restart")
    await websocket.close()
    restart_program(sys.argv[0])
