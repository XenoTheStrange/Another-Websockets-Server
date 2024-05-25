#!/usr/bin/python3
import asyncio
import sys
import os

from utils import WebsocketError, CustomLogger
from config import superusers, auth_tokens

import importlib
sys.path.append("./actions")

logger = CustomLogger("actions", "debug")

async def act(obj, username, websocket, admin=False):
    #Check if the action is a script in ./actions
    custom_modules = ", ".join(sorted([i.replace(".py","") for i in os.listdir("./actions") if ".py" in i]))
    if not f"{obj['action']}" in custom_modules:
        return str(custom_modules)

    # Import called script as module
    spec = importlib.util.spec_from_file_location(
        obj['action'], f"./actions/{obj['action']}.py")
    called_script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(called_script)

    # Call main function
    tmp = await called_script.main(obj, username, websocket, admin=admin)
    return tmp

async def do(obj, username, websocket):
    data = obj['data'] if "data" in obj else ""
    action = obj['action']
    logger.debug(f"""user: {username}, action: {action}, data: {data} """)
    isAdmin = True if username in superusers else False
    return await act(obj, username, websocket, admin=isAdmin)
