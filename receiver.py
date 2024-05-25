#!/usr/bin/python3
#
import asyncio
import websockets
import json
import base64
import subprocess
import sys
import hotReload
import actions
from customLogger import CustomLogger

logger = CustomLogger("receiver", "info")

starting_servers = [
    "127.0.0.1", 6789,
]

class WebsocketError(Exception):
    def __init__(self, message, socket, data=""):
        super().__init__(message)
        self.socket = socket
        self.message = message
        if not data == "":
            self.data = f": data:{data}"

async def custom_handler(message, websocket):
    try: obj = json.loads(message)
    except Exception: raise WebsocketError("Failed to decode JSON payload", websocket)
    username = actions.check_authorization(obj)
    if not username: raise WebsocketError("AUTH FAIL", websocket, json.dumps(obj))
    if not "action" in obj: raise WebsocketError("'action' parameter missing from request", websocket)
    if not type(obj['action']) == str: raise WebsocketError("'action' parameter missing from request", websocket)
    return await actions.do(obj, username, websocket)

async def process_message(websocket):
    message = await websocket.recv()
    logger.info(b"Received message: " + message)
    return await custom_handler(message, websocket)

def msgErrorHandler(func):
    async def inner_function(*args, **kwargs):
            try:
                await func(*args, **kwargs)
            except websockets.exceptions.ConnectionClosed:
                pass
            except ValueError as err:
                websocket.send(f"The following error occurred:\n{err}")
            except WebsocketError as err:
                await err.socket.send(err.message)
                logger.error(err.message + f"{err.data}")
    return inner_function

@msgErrorHandler
async def message_handler(websocket):
    global messages_recieved
    while True:
        response = await process_message(websocket)
        logger.info(f"Sending response: \"{response}\"")
        await websocket.send(str(response))
        # Continue listening for incoming data after processing the current message

async def main():
    asyncio.ensure_future(hotReload.handler(sys.argv[0]))
    async with websockets.serve(message_handler, *starting_servers, ping_interval=None):
        await asyncio.Future()  # Run forever (or until you cancel the server)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "restart": logger.info("Server Restarted");sys.argv[1]==""
    else: logger.info("Server Started")
    client = asyncio.run(main())
