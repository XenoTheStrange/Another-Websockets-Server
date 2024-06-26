#!/usr/bin/python3

import os
from utils import WebsocketError, check_keys, mkdir_recursive

async def main(*args, **kwargs):
    obj = args[0]
    username = args[1]
    websocket = args[2]
    if kwargs['admin']:
        return await admin(obj)
    else:
        return await user(obj, username, websocket)

async def user(obj, username, websocket):
    path = f"./user_files/{username}/"
    if not os.path.exists(path):
        mkdir_recursive(path)
    try:
        files = os.listdir(path)
    except Exception as err:
        raise WebsocketError(f"[ERROR]: {err}", websocket, path)
    files.sort()
    if len(files) == 0:
        return "No files"
    return "\n".join(files)

async def admin(obj):
    missing_keys = check_keys(["data"], obj)
    if missing_keys:
        return missing_keys
    path = obj['data'] if not obj['data'] == "" else "./"
    return os.listdir(path)