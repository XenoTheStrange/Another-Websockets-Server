#!/usr/bin/python3
#
import asyncio
import websockets
import json
import sys
import ssl

import actions
from utils import CustomLogger, WebsocketError
import config

logger = CustomLogger("receiver", "debug")

uri, port = config.host_uri

async def custom_handler(message, websocket):
    try:
        obj = json.loads(message)
    except Exception:
        raise WebsocketError("Failed to decode JSON payload", websocket)
    username = actions.check_authorization(obj)
    if not username:
        raise WebsocketError("AUTH FAIL", websocket, json.dumps(obj))
    if "action" not in obj:
        raise WebsocketError("'action' parameter missing from request", websocket)
    return await actions.do(obj, username, websocket)

async def process_message(websocket):
    message = await websocket.recv()
    try:
        message = bytes(message, "ascii")
    except TypeError:
        pass
    logger.debug(b"Received message: " + message)
    response = await custom_handler(message, websocket)
    logger.debug(f"Sending response: \"{response}\"")
    await websocket.send(str(response))

def msgErrorHandler(func):
    async def inner_function(*args, **kwargs):
            try:
                await func(*args, **kwargs)
            except websockets.exceptions.ConnectionClosed:
                pass
            except WebsocketError as err:
                await err.socket.send(err.message + f" data: {err.data}")
                logger.error(err.message + f" data: {err.data}")
            except Exception as err:
                print(type(err))
                print("Unhandled Exception: " + str(err))
    return inner_function

@msgErrorHandler
async def message_handler(websocket):
    while True:
        await process_message(websocket)
        # Continue listening for incoming data after processing the current message

async def main():
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.verify_mode = ssl.CERT_NONE
    ssl_context.load_cert_chain("./ssl/cert.pem", keyfile="./ssl/key.pem")
    async with websockets.serve(message_handler, uri, port, ping_interval=None, ssl=ssl_context):
        await asyncio.Future()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "restart":
        logger.info("Server Restarted")
        sys.argv[1]==""
    else:
        logger.info("Server Started")
    client = asyncio.run(main())
