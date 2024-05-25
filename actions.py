#!/usr/bin/python3

import json
import sys
import asyncio
import subprocess
import hotReload
from customLogger import CustomLogger

logger = CustomLogger("actions", "info")

async def run_subprocess(json_obj):
    if not "data" in json_obj: return "[ERROR]: Request does not include a command.\nInclude 'data':'command' in the json payload"
    command = json_obj['data']
    proc = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = proc.stderr if not proc.stderr == b"" else proc.stdout.decode("utf-8")
    return output

async def do(obj, username, websocket):
    action = obj['action'].lower()
    data = obj['data'] if "data" in obj else ""
    logger.info(f"""user: {username}, action: {action}, data: {data} """)
    if action == "ping":
        return "ping"
    if action == "echo":
        return json.dumps(obj)
    if action == "whoami": return username
    if action == "restart":
        await websocket.send("[INFO]: Server will restart")
        await websocket.close()
        hotReload.restart_program(sys.argv[0])
    if action == "shell":
        if username == "admin" or username == "debug": return str(await run_subprocess(obj))
        else: return "[ERROR]: NOT AUTHORIZED"
    return f"""[ERROR]: "{action}" is not a registered action"""

def check_authorization(json_obj):
    if not "auth_token" in json_obj: return False
    else: user_token = json_obj['auth_token']
    csv = open("auth_tokens.txt", "r").read().split("\n")[1:]
    if csv[-1] == "": csv.pop()
    tokens = [i.split(",")[0] for i in csv]
    users = [i.split(",")[1] for i in csv]
    for i, token in enumerate(tokens):
        if user_token == token: return users[i]
    return False
