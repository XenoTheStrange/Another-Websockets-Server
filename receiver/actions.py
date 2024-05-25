#!/usr/bin/python3
import asyncio
import json
import sys
import os
import subprocess
import random

from utils import WebsocketError, CustomLogger, file_receiver, bulk_sender, ThreadWithReturnValue, check_keys, restart_program, check_filename, mkdir_recursive
from config import superusers, auth_tokens

import importlib
sys.path.append("./actions")

logger = CustomLogger("actions", "debug")

tasks:list = [] # (task, task_name, username)

async def list_files(obj, username, websocket, admin=False):
    if admin:
        missing_keys = check_keys(["data"], obj) #username is an object
        if missing_keys:
            return missing_keys
        path = obj['data'] if not obj['data'] == "" else "./"
    else:
        path = f"./user_files/{username}/"
        if not os.path.exists(path):
            mkdir_recursive(path)
    try:
        files = os.listdir(path)
    except Exception as err:
        raise WebsocketError(f"[ERROR]: {err}", websocket, path)
    files.sort()
    try:
        files.remove("file_parts")
    except Exception:
        pass
    return "\n".join(files)

def run_subprocess(command):
    try:
        proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc.stderr if not proc.stderr == b"" else proc.stdout
    except Exception as err:
        return f"[ERROR]:subprocess: {err}"

async def wait_for_subprocess(obj, username):
    missing_keys = check_keys(["data"],obj)
    if missing_keys:
        return missing_keys
    command = obj['data'].split("$&svdlm$&")
    thread = ThreadWithReturnValue(target=run_subprocess, args=[command])
    thread.start()
    while True:
        await asyncio.sleep(0.1)
        if thread.is_alive():
            continue
        try:
            return thread.join().decode()
        except Exception:
            return thread.join()
        await asyncio.sleep(1)

async def list_tasks(username, websocket):#CURRENT
    global tasks
    lst = []
    for task in tasks:
        if task[2] == username:
            lst.append(task[1])
    if lst == []:
        return "No tasks remain"
    return ", ".join(lst)

async def start_task(obj, username, func):
    missing_keys = check_keys(["name"],obj)
    if missing_keys:
        return missing_keys
    global tasks
    for task in tasks:
        if obj['name'] == task[1]:
            return f"[ERROR]: A task with that name already exists: \"{obj['name']}\""
    result = asyncio.create_task(func(obj, username))
    tasks.append((result, obj['name'], username))
    return "[INFO]: Task started."

async def check_task(obj, username, websocket):
    global tasks
    missing_keys = check_keys(["data"], obj)
    if missing_keys:
        return missing_keys
    taskname = obj['data']
    for task in tasks:
        result = task[0]
        if task[2] == username and task[1] == taskname:
            if not result.done():
                return "[INFO]: Task is still running."
            # if we haven't returned yet then the task is done and we need to send its return value and remove it from the task list.
            tasks.remove(task)
            try:
                return result.result()
            except Exception as err:
                logger.error(err)
                return str(err)
    # if we finished going through the tasks without returning then there was no username/taskname match
    return f"There is no task with that name: {taskname}"


async def act(obj, username, websocket):
    #Check if the action is a script in ./actions
    custom_modules = [i for i in os.listdir("./actions") if ".py" in i]
    if not f"{obj['action']}.py" in custom_modules:
        return str(custom_modules)

    # Import called script as module
    spec = importlib.util.spec_from_file_location(
        obj['action'], f"./actions/{obj['action']}.py")
    called_script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(called_script)

    # Call main function
    tmp = await called_script.main(obj, username, websocket)
    return tmp

async def do(obj, username, websocket):
    action = obj['action'].lower()
    data = obj['data'] if "data" in obj else ""
    logger.debug(f"""user: {username}, action: {action}, data: {data} """)
    return await act(obj, username, websocket)
    """match action:
        case "ping":
            return "ping"
        case "echo":
            return json.dumps(obj)
        case "whoami":
            return username
        case "restart": #DONE
            await websocket.send("[INFO]: Server will restart")
            await websocket.close()
            restart_program(sys.argv[0])
        case "kill" | "stop":
            logger.info(f"[INFO]: Server kill received from {username}")
            await websocket.send("[INFO]: Server will stop.")
            await websocket.close()
            sys.exit()
        case "shell":
            if username in superusers:
                return await wait_for_subprocess(obj, username)
        case "shell_task":
            if username in superusers:
                return await start_task(obj, username, wait_for_subprocess)
        case "get_file": #DONE
            return await send_file(obj, username, websocket)
        case "admin_get_file":
            if username in superusers:
                return await send_file(obj, username, websocket, admin=True)
        case "list_files":
            return await list_files(obj, username, websocket)
        case "ls":
            if username in superusers:
                return await list_files(obj, username, websocket, admin=True)
        case "send_file": #DONE
            return await recv_file(obj, username, websocket)
        case "list_tasks":
            return await list_tasks(username, websocket)
        case "check_task":
            return await check_task(obj, username, websocket)
    return f"[ERROR]: "{action}" is not a registered action"
    """

async def check_authorization(obj):
    """Returns a username if the auth_token is valid."""
    if "auth_token" not in obj:
        return False
    else:
        user_token = obj['auth_token']
        for entry in auth_tokens:
            if entry[0] == user_token:
                return entry[1]
    await asyncio.sleep(random.random()*2)
    return False
