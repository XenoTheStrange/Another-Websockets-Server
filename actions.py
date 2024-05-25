#!/usr/bin/python3

import json
import sys
import os
import subprocess
import hotReload
from customLogger import CustomLogger
import base64
from receiver import WebsocketError
import asyncio
from threading import Thread

class ThreadWithReturnValue(Thread):
    def __init__(self, group=None, target=None, name=None,args=(), kwargs={}, Verbose=None):
        Thread.__init__(self, group, target, name, args, kwargs)
        self._return = None
    def run(self):
        if self._target is not None:
            self._return = self._target(*self._args,**self._kwargs)
    def join(self, *args):
        Thread.join(self, *args)
        return self._return

logger = CustomLogger("actions", "info")

tasks = [] #This will contain subprocess tasks or something like that.

def check_keys(keys, obj):
    missing=[]
    for key in keys:
        if key not in obj: missing.append(key)
    if missing == []: return False
    out = " ".join([f"'{i}'," for i in missing])[:-1] # 'key', 'key2', 'key3' # [:-1] removes the end comma
    return f"""[ERROR]: Missing keys in json data: {out}"""

def thread_subprocess(command):
    proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.stderr if not proc.stderr == b"" else proc.stdout

async def wait_for_subprocess(obj={}, cmd_internal=False):
    """This will block the main event loop until the subprocess returns. Need to implement with threading and polling."""
    if cmd_internal:
        command = cmd_internal
    else:
        missing_keys = check_keys(["data"],obj)
        if missing_keys: return missing_keys
        command = obj['data'].split(" ")
    try:
        thread = ThreadWithReturnValue(target=thread_subprocess, args=[command])
        thread.start()
        while True:
            await asyncio.sleep(0.1)
            if not thread.is_alive():
                return thread.join()
            else:
                await asyncio.sleep(1)
        #proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        #return proc.stderr if not proc.stderr == b"" else proc.stdout
    except Exception as err:
        return err

async def get_file(obj):
    return "NOT IMPLEMENTED"

async def assemble_file(filename, user_path, parts_list):
    parts_list.sort()
    parts_path = f"{user_path}/file_parts"
    with open(f"{user_path}/{filename}", "wb") as file:
        for part in parts_list:
            data = open(f"{parts_path}/{part}", "rb").read()
            conv = base64.b64decode(data)
            file.write(conv)
    if os.path.exists(f"{user_path}/{filename}"):
        for file in parts_list:
            os.remove(f"{user_path}/file_parts/{file}")
        return "[INFO]: File was written"

async def get_next_part(parts_list, total_parts):
    parts = [int(i.split(".")[-1]) for i in parts_list]
    parts.sort()
    for i, pnum in enumerate(parts):
        if not i+1 == int(pnum): return i+1
    if len(parts) < int(total_parts): return len(parts)+1
    return None

async def recv_file(obj, username, websocket): #next step is to recieve file chunks and save them to disk temporarily and if they're part 10/10 then assemble the file in question'
    missing_keys = check_keys(["filename", "data", "part"],obj)
    if missing_keys: return missing_keys
    user_path = f"./user_files/{username}"
    parts_path = f"{user_path}/file_parts"
    filename = obj['filename']
    if not os.path.exists(user_path): os.mkdir(user_path)
    if not os.path.exists(parts_path): os.mkdir(parts_path)
    #TODO
    if "../" in filename: raise WebsocketError("[ERROR]: Backward navigaion detected in the file path.", websocket, filename)
    if "\\" in filename or "/" in filename: raise WebsocketError("[ERROR]: Filename contains a path", websocket, filename)
    if filename[-1] == "/": raise WebsocketError("[ERROR]: Path does not include a file name.", websocket, filename)
    if ".srres.part" in filename: raise WebsocketError("[ERROR]: filename cannot include \".srres.part\". This is a reserved keyword", websocket, filename)
    if filename[0] == "/": filename = filename[1:]
    total_parts = obj['part'].split("/")[1]
    parts_list = [i for i in os.listdir(parts_path) if f"{filename}.srres.part" in i]
    part = obj['part'].split("/")[0].zfill(len(total_parts)) #the zfill is necessary or the tmp files are assembled incorrectly
    full_filepath = f"{parts_path}/{filename}.srres.part.{part}"
    with open(full_filepath, "wb") as file:
        file.write(bytes(obj['data'],"ascii"))
    parts_list = [i for i in os.listdir(parts_path) if f"{filename}.srres.part" in i]
    next_part = await get_next_part(parts_list, total_parts)
    if next_part is not None:
        return f"OK: {int(part)}/{next_part}/{total_parts}"
    return await assemble_file(filename, user_path, parts_list)

# async def ffmpeg_delegate(obj):
#     return "NOT IMPLEMENTED"
#     missing_keys = check_keys(["filepath","data"],obj)
#     if missing_keys: return missing_keys
#     command = ["ffmpeg"] + obj['command'].split(" ")
#     return await wait_for_subprocess(cmd_internal=command) #this will be used to call ffmpeg

async def do(obj, username, websocket):
    action = obj['action'].lower()
    data = obj['data'] if "data" in obj else ""
    logger.debug(f"""user: {username}, action: {action}, data: {data} """)
    match action:
        case "ping": return "ping"
        case "echo": return json.dumps(obj)
        case "whoami": return username
        case "restart":
            await websocket.send("[INFO]: Server will restart")
            await websocket.close()
            hotReload.restart_program(sys.argv[0])
        case "stop", "kill":
            await websocket.send("[INFO]: Server will stop")
            await websocket.close()
            exit()
        case "shell":
            if username == "admin" or username == "debug":
                return str(await wait_for_subprocess(obj))
            else: return "[ERROR]: NOT AUTHORIZED"
        case "get_file": return await get_file(obj, username)
        case "send_file": return await recv_file(obj, username, websocket)
    return f"""[ERROR]: "{action}" is not a registered action"""

def check_authorization(obj):
    if "auth_token" not in obj:
        return False
    else:
        user_token = obj['auth_token']
    csv = open("auth_tokens.txt", "r").read().split("\n")[1:]
    if csv[-1] == "":
        csv.pop()
    tokens = [i.split(",")[0] for i in csv]
    users = [i.split(",")[1] for i in csv]
    for i, token in enumerate(tokens):
        if user_token == token: return users[i]
    return False
