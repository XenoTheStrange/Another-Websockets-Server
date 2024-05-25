import asyncio
import subprocess
from threading import Thread
from utils import check_keys 

tasks:list = [] # (task, task_name, username) #TODO this does nothing

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

async def main(*args, **kwargs):
    obj = args[0]
    username = args[1]
    websocket = args[2]
    if not kwargs['admin']:
        return "[ERROR] ACCESS DENIED"
    missing_keys = check_keys(["tasker-cmd", "data"],obj)
    if missing_keys:
        return missing_keys
    if obj['tasker-cmd'] == "shell":
        return await wait_for_subprocess(obj)
    #elif obj['tasker-cmd'] == "shell_task":
    #    return await start_task(obj, username)
    #TODO Task system doesn't work because the output is discarded when it's done running and needs to be saved in a text file or something
    #storing that stuff in memory doesn't work when the script is being imported, run and closed over and over.
    return "Function Not Done"

def run_subprocess(command):
    try:
        proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return proc.stderr if not proc.stderr == b"" else proc.stdout
    except Exception as err:
        return f"[ERROR]:subprocess: {err}"

async def wait_for_subprocess(obj):
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

async def start_task(obj, username):
    missing_keys = check_keys(["name"],obj)
    if missing_keys:
        return missing_keys
    global tasks
    for task in tasks:
        if obj['name'] == task[1]:
            return f"[ERROR]: A task with that name already exists: \"{obj['name']}\""
    result = asyncio.create_task(wait_for_subprocess(obj))
    tasks.append((result, obj['name'], username))
    return "[OK]: Task started."

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

async def list_tasks(username):#CURRENT
    global tasks
    lst = []
    for task in tasks:
        if task[2] == username:
            lst.append(task[1])
    if lst == []:
        return "No tasks remain"
    return ", ".join(lst)