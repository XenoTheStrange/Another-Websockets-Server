#!/usr/bin/python3
import asyncio
import json
import sys
import os
import subprocess

from utils import WebsocketError, CustomLogger, file_receiver, bulk_sender, ThreadWithReturnValue, check_keys, restart_program, check_filename
from config import superusers, auth_tokens

logger = CustomLogger("actions", "info")

async def list_files(username, websocket):
    files = os.listdir(f"./user_files/{username}")
    files.sort()
    files.remove("file_parts")
    return ", ".join(files)

async def send_file(obj, username, websocket):
    missing_keys = check_keys(["filename"], obj)
    if missing_keys:
        return missing_keys
    await check_filename(obj['filename'], websocket)
    filepath = f"./user_files/{username}/{obj['filename']}"
    if not os.path.exists(filepath):
        raise WebsocketError("[ERROR]: There is no file at that path.", websocket, filepath)
    sender = bulk_sender(filepath, 1024*500)#this is a safe number for websockets. Still kind of small. Around 500kb worth of data (+ other parts of the request)
    for chunk in sender:
        await websocket.send(json.dumps(chunk))
        response = await websocket.recv()
        logger.info(bytes(f"Received response: \"{response}\"","utf-8"))
        if "[INFO]: File was written" in response:
            break
        #skip parts the server has indicated already exist
        next_chunk = response.split(": ")[1].split("/")[1]
        print(next_chunk)
        while int(chunk['part'].split("/")[0])+1 < int(next_chunk):
            next(sender)['part']
    return "[INFO] DONE SENDING"

def run_subprocess(command):
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.stderr if not proc.stderr == b"" else proc.stdout

async def wait_for_subprocess(obj={}, cmd_internal=False):
    if cmd_internal:
        command = cmd_internal
    else:
        missing_keys = check_keys(["data"],obj)
        if missing_keys:
            return missing_keys
        command = obj['data'].split("$&svdlm$&")
        thread = ThreadWithReturnValue(target=run_subprocess, args=[command])
        thread.start()
        while True:
            await asyncio.sleep(0.1)
            if not thread.is_alive():
                try:
                    return thread.join().decode()
                except Exception:
                    return thread.join()
            else:
                await asyncio.sleep(1)

async def recv_file(obj, username, websocket):
    missing_keys = check_keys(["filename", "data", "part"],obj)
    if missing_keys:
        return missing_keys
    recvfile = file_receiver(obj, username, websocket)
    return await recvfile.main()

async def do(obj, username, websocket):
    action = obj['action'].lower()
    data = obj['data'] if "data" in obj else ""
    logger.debug(f"""user: {username}, action: {action}, data: {data} """)
    match action:
        case "ping":
            return "ping"
        case "echo":
            return json.dumps(obj)
        case "whoami":
            return username
        case "restart":
            await websocket.send("[INFO]: Server will restart")
            await websocket.close()
            restart_program(sys.argv[0])
        case "kill" | "stop":
            logger.info("[INFO]: Server shutting down gracefully.")
            await websocket.send("[INFO]: Server will stop.")
            await websocket.close()
            exit()
        case "shell":
            if username in superusers:
                return await wait_for_subprocess(obj)
            else:
                return "[ERROR]: NOT AUTHORIZED"
        case "get_file":
            return await send_file(obj, username, websocket)
        case "list_files":
            return await list_files(username, websocket)
        case "send_file":
            return await recv_file(obj, username, websocket)
    return f"""[ERROR]: "{action}" is not a registered action"""

def check_authorization(obj):
    """Returns a username if the auth_token is valid."""
    if "auth_token" not in obj:
        return False
    else:
        user_token = obj['auth_token']
        for entry in auth_tokens:
            if entry[0] == user_token:
                return entry[1]
    return False
