import asyncio
import subprocess
from threading import Thread
from utils import check_keys 

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
    missing_keys = check_keys(["data"],obj)
    if missing_keys:
        return missing_keys
    return await wait_for_subprocess(obj)

def run_subprocess(command):
    try:
        proc = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        return proc.stderr if not proc.stderr == b"" else proc.stdout
    except Exception as err:
        return f"[ERROR]:subprocess: {err}"

async def wait_for_subprocess(obj):
    missing_keys = check_keys(["data"],obj)
    if missing_keys:
        return missing_keys
    thread = ThreadWithReturnValue(target=run_subprocess, args=[obj['data']])
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

