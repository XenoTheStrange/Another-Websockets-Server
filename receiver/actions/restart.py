#!/usr/bin/python3

import sys
import psutil
import os

sys.path.append("/hdd/desktop/delegator/server/receiver/")

async def main(*args, **kwargs):
    if not kwargs['admin']:
        return "[ERROR] ACCESS DENIED"
    websocket = args[2]
    await websocket.send("[OK]: Server will restart")
    await websocket.close()
    try:
        restart_program_psutil(sys.argv[0])
    except Exception as e:
        print(e)
        pass
    "If psutil isn't installed or fails for some reason, try again anyway without cleanups"
    os.execl(sys.argv[0], sys.argv[0], "restart")

def restart_program_psutil(filepath, auto=False):
    """Restarts the current program, with file objects and descriptors cleanup"""
    p = psutil.Process(os.getpid())
    for handler in p.open_files() + p.connections():
        os.close(handler.fd)
    os.execl(filepath, filepath, "restart")