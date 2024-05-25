#!/usr/bin/python3

import asyncio
import websockets
from time import sleep
import json
import sys
import base64
from customLogger import CustomLogger

logger = CustomLogger("sender", "info")

host_url = "ws://localhost:6789"
auth_token = "0xDEADBEEF" #0xDEADBEEF

def handleErrors(func):
    async def inner_function(*args, **kwargs):
        try:
            await func(*args, **kwargs)
        except OSError as err:
            logger.error("Connection failed")
        except websockets.exceptions.ConnectionClosedError:
            logger.error("ConnectionClosedUnexpected")
        except websockets.exceptions.ConnectionClosedOK:
            logger.error("ConnectionClosedOK")
    return inner_function

def create_payload(data):
    return json.dumps(data)

async def send_message(payload, websocket):
        await websocket.send(bytes(payload, "utf-8"))
        logger.info(bytes(f"Sent Message: {payload}","utf-8"))
        response = await websocket.recv()
        logger.info(bytes(f"Received response: \"{response}\"","utf-8"))
        print(str(response))

@handleErrors
async def main(auth_token, action, data):
    async with websockets.connect(host_url) as websocket:
        data = {
            'auth_token':auth_token,
            'action': action,
            'data': data
            }
        payload = create_payload(data)
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
