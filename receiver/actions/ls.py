#!/usr/bin/python3

import os

async def main(*args):
    obj = args[0]
    username = args[1]
    websocket = args[2]
    if obj['data'] == "":
        obj['data'] = "./"
    return os.listdir(obj['data'])

