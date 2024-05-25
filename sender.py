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

#host_url = "ws://localhost:6789"
host_url = "wss://127.0.0.1:6789"
auth_token = "Press F to pay respects..." #0xDEADBEEF

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
    sender = bulk_sender(filepath, 1024*500)#this is a safe number for websockets. Still kind of
    for chunk in sender:
        await websocket.send(json.dumps(chunk))
        response = await websocket.recv()
        logger.info(bytes(f"Received response: \"{response}\"","utf-8"))
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
    print(response)

@handleErrors
async def main(auth_token, action, data):
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    async with websockets.connect(host_url, ssl=ssl_context) as websocket:
        match action:
            case "send_file":
                await send_file(data, auth_token, websocket)
            case "get_file":
                await get_file(data, auth_token, websocket)
            case _:
                obj = {
                    'auth_token':auth_token,
                    'action': action,
                    'data': data
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
    data = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
    client = asyncio.run(main(auth_token, action, data))
