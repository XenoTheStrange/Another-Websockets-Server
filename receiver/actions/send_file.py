#!/usr/bin/python3

import os
import sys
import json

sys.path.append("/hdd/desktop/delegator/server/receiver/")
from utils import check_filename, WebsocketError, bulk_sender, check_keys, CustomLogger, file_receiver

logger = CustomLogger("send_file", "info")

async def main(*args):
    obj = args[0]
    username = args[1]
    websocket = args[2]
    return await recv_file(obj, username, websocket)

async def recv_file(obj, username, websocket):
    missing_keys = check_keys(["filename", "data", "part"],obj)
    if missing_keys:
        return missing_keys
    recvfile = file_receiver(obj, username, websocket)
    tmp = await recvfile.main()
    print(tmp)
    return tmp
