#!/usr/bin/python3

import json

async def main(*args, **kwargs):
    return json.dumps(args[0])
