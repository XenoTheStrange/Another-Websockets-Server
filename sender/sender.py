#!/usr/bin/python3

import asyncio
import websockets
import json
import sys
from customLogger import CustomLogger
import base64
import os
import math
import ssl

logger = CustomLogger("sender", "info")

host_url = "wss://192.168.1.30:6789"
auth_token = "0xDEADBEEF" #0xDEADBEEF

def handleErrors(func):
    async def inner_function(*args, **kwargs):
        try:
            await func(*args, **kwargs)
        except OSError as err:
            logger.error(err)
        #except websockets.exceptions.ConnectionClosedError:
        #    logger.error("ConnectionClosedUnexpected")
        except websockets.exceptions.ConnectionClosedOK:
            logger.error("ConnectionClosedOK")
    return inner_function

class file_receiver():
    def __init__(self, obj, filename):
        self.fn = filename
        self.savepath = "./received_files"
        self.parts_path = f"{self.savepath}/file_parts"
        self.total_parts = obj['part'].split("/")[1]
        self.parts_list = [] # this will be filled in when get_parts_list is called
        self.partstr = obj['part'].split("/")[0].zfill(len(self.total_parts)) # the number of this part with zeros so array sorting works
        self.filepath = f"{self.parts_path}/{self.fn}.srres.part.{self.partstr}"
        self.data = obj['data']
    async def mk_path(self, path): # helper function to avoid repetitive code in ensure_paths()
        if not os.path.exists(path):
            os.mkdir(path)
    async def ensure_paths(self): #make sure folders exist
        await self.mk_path(self.savepath)
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
        with open(f"{self.savepath}/{self.fn}", "wb") as file:
            for part in self.parts_list:
                data = open(f"{self.parts_path}/{part}", "rb").read()
                conv = base64.b64decode(data)
                file.write(conv)
        if os.path.exists(f"{self.savepath}/{self.fn}"):
            for file in self.parts_list:
                os.remove(f"{self.savepath}/file_parts/{file}")
        return "[INFO]: File was written"
    async def main(self):
        await self.ensure_paths()
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
            'auth_token':auth_token,
            'action': "send_file",
            'filename': filepath.split("/")[-1],
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

async def send_message(payload, websocket):
    try:
        await websocket.send(bytes(payload, "utf-8"))
        response = await websocket.recv()
        logger.debug(bytes(f"Received response: \"{response}\"","utf-8"))
        print(str(response))
    except TimeoutError:
        logger.error("Connection timed out. Host is busy.")

async def send_file(filepath, auth_token, websocket):
    sender = bulk_sender(filepath, 1024*500)#this is a safe number for websockets. Still kind of small. Around 500kb worth of data (+ other parts of the request)
    for chunk in sender:
        await websocket.send(json.dumps(chunk))
        response = await websocket.recv()
        logger.info(bytes(f"Received response: \"{response}\"","utf-8"))
        if "[ERROR]" in response:
            print(response)
            break
        if "[INFO]: File was written" in response:
            break
        #skip parts the server has indicated already exist
        next_chunk = response.split(": ")[1].split("/")[1]
        while int(chunk['part'].split("/")[0])+1 < int(next_chunk):
            next(sender)['part']

async def get_file(filename, auth_token, websocket):
    obj = {
        'auth_token':auth_token,
        'action': "get_file",
        'filename': filename
    }
    payload = json.dumps(obj)
    await websocket.send(payload)
    response = await websocket.recv()
    while True:
        if "[ERROR]" in response:
            print(response)
            break
        if "[INFO] DONE SENDING" in response:
            print("File Received.")
            return
        obj = json.loads(response)
        print(f"Got part: {obj['part']}")
        recvfile = file_receiver(obj, filename)
        next = await recvfile.main()
        await websocket.send(next)
        response = await websocket.recv()

@handleErrors
async def main(auth_token, action, data):
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    async with websockets.connect(host_url, ssl=ssl_context) as websocket:
        match action:
            case "send_file":
                await send_file(data[0], auth_token, websocket)
            case "get_file":
                await get_file(data[0], auth_token, websocket)
            case _:
                obj = {
                    'auth_token':auth_token,
                    'action': action,
                    'data': " ".join(data)
                }
                payload = json.dumps(obj)
                await send_message(payload, websocket)
        await websocket.close()

if __name__ == "__main__":
    #This is a janky way of handling arguments; I haven't learned how to use a parser yet. TODO '
    if "help" in sys.argv[1] or "-h" in sys.argv[1] or "--h" in sys.argv[1] or "--help" in sys.argv[1]:
        print("""USAGE: ./sender.py action [data]""")
        exit()
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    data = sys.argv[2:] if len(sys.argv) > 2 else ""
    client = asyncio.run(main(auth_token, action, data))
