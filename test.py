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
        await sender.shell_command(["sleep","10"], api_key, socket, task=True, name="test")
        #await sender.shell_command(["ls","./"], api_key, socket, task=True, name="test")
        while True:
            tmp = await sender.check_task("test", api_key, socket)
            print(tmp)
            if "still running" not in tmp:
                break
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
