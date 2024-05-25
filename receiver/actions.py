#!/usr/bin/python3

import json
import sys
import os
import subprocess
import hotReload
from customLogger import CustomLogger
import base64
from errors import WebsocketError
import asyncio
from threading import Thread
import math

logger = CustomLogger("actions", "info")

async def check_filename(filename, websocket): #make sure the filename is safe, just a name and not a path
    if "../" in filename:
        raise WebsocketError("[ERROR]: Backward navigaion detected in the file path.", websocket, filename)
    if "\\" in filename or "/" in filename:
        raise WebsocketError("[ERROR]: Filename contains a path.", websocket, filename)
    if filename == "":
        raise WebsocketError("[ERROR]: Filename is empty.", websocket, filename)
    if ".srres.part" in filename:
        raise WebsocketError("[ERROR]: Filename cannot include \".srres.part\". This is a reserved keyword", websocket, filename)

class file_receiver():
    def __init__(self, obj, username, websocket):
        self.socket = websocket
        self.fn = obj['filename']
        self.user_path = f"./user_files/{username}"
        self.parts_path = f"{self.user_path}/file_parts"
        self.total_parts = obj['part'].split("/")[1]
        self.parts_list = [] # this will be filled in when get_parts_list is called
        self.partstr = obj['part'].split("/")[0].zfill(len(self.total_parts)) # the number of this part with zeros so array sorting works
        self.filepath = f"{self.parts_path}/{self.fn}.srres.part.{self.partstr}"
        self.data = obj['data']
    async def mk_path(self, path): # helper function to avoid repetitive code in ensure_paths()
        if not os.path.exists(path):
            os.mkdir(path)
    async def ensure_paths(self): #make sure folders exist
        await self.mk_path("./user_files")
        await self.mk_path(self.user_path)
        await self.mk_path(self.parts_path)
    async def get_parts_list(self): #updates the object's parts list
        self.parts_list = [i for i in os.listdir(self.parts_path) if f"{self.fn}.srres.part" in i]
        self.parts_list.sort()
    async def write_part(self):
        with open(self.filepath, "wb") as file:
            file.write(bytes(self.data,"ascii"))
    async def get_next_part(self): #returns the number for which part is needed next
        await self.get_parts_list()
        parts = [int(i.split(".")[-1]) for i in self.parts_list] #returns a list of numbers for each part we have
        parts.sort()
        for i, pnum in enumerate(parts):
            if not i+1 == int(pnum):
                return i+1
            if len(parts) < int(self.total_parts):
                return len(parts)+1
        return None
    async def assemble_file(self): #put that bad boy together and delete the parts
        await self.get_parts_list()
        with open(f"{self.user_path}/{self.fn}", "wb") as file:
            for part in self.parts_list:
                data = open(f"{self.parts_path}/{part}", "rb").read()
                conv = base64.b64decode(data)
                file.write(conv)
        if os.path.exists(f"{self.user_path}/{self.fn}"):
            for file in self.parts_list:
                os.remove(f"{self.user_path}/file_parts/{file}")
        return "[INFO]: File was written"
    async def main(self):
        await self.ensure_paths()
        await check_filename(self.fn, self.socket)
        await self.write_part()
        next_part = await self.get_next_part()
        if next_part is not None:
            return f"OK: {int(self.partstr)}/{next_part}/{self.total_parts}"
        return await self.assemble_file()

def bulk_sender(filepath, chunk_size):
    with open(filepath, "rb") as f:
        file_data = f.read()
        size = os.stat(filepath).st_size
        total_chunks = math.ceil(size/chunk_size)
        payload = {
            'data': "",
            'part': ""
        }
        part = 1
        while True:
            if len(file_data) > 0:
                payload['data'] = base64.b64encode(file_data[:chunk_size]).decode()
                payload['part'] = f"{part}/{total_chunks}"
                part+=1
                yield payload
                file_data = file_data[chunk_size:]
            else:
                break

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

def check_keys(keys, obj):
    missing=[]
    for key in keys:
        if key not in obj:
            missing.append(key)
    if missing == []:
        return False
    out = " ".join([f"'{i}'," for i in missing])[:-1] # 'key', 'key2', 'key3' # [:-1] removes the end comma
    return f"""[ERROR]: Missing keys in json data: {out}"""

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
        command = obj['data'].split(" ")
        thread = ThreadWithReturnValue(target=run_subprocess, args=[command])
        thread.start()
        while True:
            await asyncio.sleep(0.1)
            if not thread.is_alive():
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
            hotReload.restart_program(sys.argv[0])
        case "stop", "kill":
            await websocket.send("[INFO]: Server will stop")
            await websocket.close()
            exit()
        case "shell":
            if username == "admin" or username == "debug":
                return str(await wait_for_subprocess(obj))
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
        if user_token == token:
            return users[i]
    return False
