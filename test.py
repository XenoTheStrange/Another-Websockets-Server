#!/usr/bin/python3
import sys
import asyncio

#import py script from another directory by adding it to the system path
sys.path.append("./sender")
import sender


host_url = "wss://192.168.1.30:6789"
api_key = "0xDEADBEEF"

async def main():
    async with await sender.server_connect(host_url) as socket:
        response = await sender.arbitrary_command(["get_files",""], api_key, socket)
        print(response)

if __name__ == "__main__":
    asyncio.run(main())
