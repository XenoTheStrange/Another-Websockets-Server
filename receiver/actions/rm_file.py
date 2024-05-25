#!/usr/bin/python3

import os
from utils import check_filename, WebsocketError, check_keys, mkdir_recursive

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
    fname = obj['data']
    await check_filename(fname, websocket)
    try:
        os.remove(f"{path}/{fname}")
        return f"[OK] File \"{fname}\" was deleted"
    except FileNotFoundError:
        return f"[ERROR] File not found: \"{fname}\""
    except Exception as err:
        raise WebsocketError(f"[ERROR]: {err}", websocket, path)


async def admin(obj):
    missing_keys = check_keys(["data"], obj)
    if missing_keys:
        return missing_keys
    path = obj['data'] if not obj['data'] == "" else "./"
    return os.listdir(path)