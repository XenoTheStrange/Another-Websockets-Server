#!/usr/bin/python3
import logging
import sys
import os
import math
import base64
from typing import Any

import config

class CustomLogger:
    def __init__(self, name: str, logLevel):
        self._name = name
        match logLevel.lower():
            case "debug":
                level = logging.DEBUG
            case "info":
                level = logging.INFO
            case "warn":
                level = logging.WARN
            case "error":
                level = logging.ERROR
            case "critical":
                level = logging.CRITICAL
            case "fatal":
                level = logging.FATAL
            case _:
                level = logging.DEBUG
        logging.basicConfig(stream=sys.stdout, level=level)
        # Create a logger
        self._logger = logging.getLogger(self._name)
        # Add file handler
        current_dir = os.path.dirname(__file__)
        if not os.path.exists(os.path.join(current_dir, 'logs')):
            os.mkdir(os.path.join(current_dir, 'logs'))
        log_filename = os.path.join(current_dir, f'logs/{self._name}.log')
        file_handler = logging.FileHandler(log_filename, mode='a')
        file_handler.setLevel(logging.DEBUG)
        self._logger.addHandler(file_handler)
    def debug(self, message: Any, data=""): return self._logger.debug(f'{message}')
    def info(self, message: Any, data=""): return self._logger.info(f'{message}')
    def warning(self, message: Any, data=""): return self._logger.warning(f'{message}')
    def error(self, message: Any, data=""): return self._logger.error(f'{message}')
    def critical(self, message: Any, data=""): return self._logger.critical(f'{message}')

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
            'auth_token':config.auth_token,
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
