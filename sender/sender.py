#!/usr/bin/python3

import asyncio
import websockets
import json
import sys
import ssl

from utils import bulk_sender, file_receiver, CustomLogger
import config

logger = CustomLogger("sender", "info")

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

async def send_message(payload, websocket):
    try:
        await websocket.send(bytes(payload, "utf-8"))
        response = await websocket.recv()
        logger.debug(bytes(f"Received response: \"{response}\"","utf-8"))
        return response
    except TimeoutError:
        logger.error("Connection timed out. Host is busy.")

async def send_file(filepath, auth_token, websocket):
    sender = bulk_sender(filepath, 1024*500)#this is a safe number for websockets. Still kind of small. Around 500kb worth of data (+ other parts of the request)
    for chunk in sender:
        await websocket.send(json.dumps(chunk))
        response = await websocket.recv()
        logger.debug(bytes(f"Received response: \"{response}\"","utf-8"))
        print(response)
        if "[ERROR]" in response:
            logger.error(bytes(f"An error occured: \"{response}\"" ,"utf-8"))
            return response
        if "[INFO]: File was written" in response:
            return "OK"
        #skip parts the server has indicated already exist
        next_chunk = response.split(": ")[1].split("/")[1]
        while int(chunk['part'].split("/")[0])+1 < int(next_chunk):
            next(sender)['part']

async def get_file(filename, auth_token, websocket, admin=False):
    obj = {
        'auth_token':auth_token,
        'action': "admin_get_file" if admin else "get_file",
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
            return response
        obj = json.loads(response)
        print(f"Got part: {obj['part']}")
        recvfile = file_receiver(obj, filename.split("/")[-1], savepath=config.download_path)
        next = await recvfile.main()
        await websocket.send(next)
        response = await websocket.recv()

async def shell_command(data, auth_token, websocket, task=False, name="shell_cmd"):
    shelltype = "shell" if task == False else "shell_task"
    obj = {
    'auth_token':auth_token,
    'action': shelltype,
    'name': name,
    'data': "$&svdlm$&".join(data)
    }
    payload = json.dumps(obj)
    response = await send_message(payload, websocket)
    return response

async def check_task(taskname, auth_token, websocket):
    obj = {
    'auth_token':auth_token,
    'action': "check_task",
    'data': taskname
    }
    payload = json.dumps(obj)
    return await send_message(payload, websocket)

async def arbitrary_command(data, auth_token, websocket):
    obj = {
    'auth_token':auth_token,
    'action': data[0],
    'data': " ".join(data[1:])
    }
    payload = json.dumps(obj)
    return await send_message(payload, websocket)

async def server_connect(host_url):
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    socket = websockets.connect(host_url, ssl=ssl_context)
    return socket

@handleErrors
async def main(auth_token, action, data):
    async with await server_connect(config.host_url) as websocket:
        match action:
            case "send_file":
                print(await send_file(data[0], auth_token, websocket))
            case "get_file":
                print(await get_file(data[0], auth_token, websocket))
            case "admin_get_file":
                print(await get_file(data[0], auth_token, websocket, admin=True))
            case "shell":
                print(await shell_command(data, auth_token, websocket))
            case "shell_task":
                print(await shell_command(data, auth_token, websocket, task=True))
            case _:
                data = [action]+[data] if isinstance(data,str) else [action]+data #make sure data variable is a list of strings
                print(await arbitrary_command(data, auth_token, websocket))
        await websocket.close()

def print_help():
    print("""USAGE: ./sender.py action [data]""")
    exit()

if __name__ == "__main__":
    #This is mainly for testing purposes as the module is intended to be used in scripts
    if len(sys.argv) < 2:
        print_help()
    if sys.argv[1] in ["help","-h","--h","--help"]:
        print_help()
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    data = sys.argv[2:] if len(sys.argv) > 2 else ""
    client = asyncio.run(main(config.auth_token, action, data))
