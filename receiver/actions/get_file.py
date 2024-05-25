#!/usr/bin/python3

import os
import sys
import json

sys.path.append("/hdd/desktop/delegator/server/receiver/")
from utils import check_filename, WebsocketError, bulk_sender, check_keys, CustomLogger

logger = CustomLogger("actions", "debug")

async def main(*args, **kwargs):
    print(args)
    obj = args[0]
    username = args[1]
    websocket = args[2]
    return await send_file(obj, username, websocket, admin=False)

async def send_file(obj, username, websocket, admin=False):
    missing_keys = check_keys(["filename"], obj)
    if missing_keys:
        return missing_keys
    if admin:
        filepath = obj['filename']
    else:
        await check_filename(obj['filename'], websocket)
        filepath = f"./user_files/{username}/{obj['filename']}"
    if not os.path.exists(filepath):
        raise WebsocketError("[ERROR]: There is no file at that path.", websocket, filepath)
    sender = bulk_sender(filepath, 1024*500)#this is a safe number for websockets. Still kind of small. Around 500kb worth of data (+ other parts of the request)
    print(f"Sending file: {obj['filename']}")
    for chunk in sender:
        await websocket.send(json.dumps(chunk))
        response = await websocket.recv()
        logger.debug(bytes(f"Received response: \"{response}\"","utf-8"))
        if "[INFO]: File was written" in response:
            break
        #skip parts the server has indicated already exist
        next_chunk = response.split(": ")[1].split("/")[1]
        while int(chunk['part'].split("/")[0])+1 < int(next_chunk):
            next(sender)['part']
    return "[INFO] DONE SENDING"
