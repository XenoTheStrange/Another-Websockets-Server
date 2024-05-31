#!/usr/bin/python3
import sys
import asyncio
#import py script from another directory by adding it to the system path
sys.path.append("./sender")
import sender
from utils import CustomLogger

logger = CustomLogger("sender", "debug")

host_url = "wss://192.168.1.30:6789"
api_key = "0xDEADBEEF"

#NOTE: Requires test.mkv to be in the same directory as this script

"""Edit this function to start the tasks you need"""
async def do_tasks(socket):
    logger.info("Connected. Beginning work:")
    await sender.send_file("./test.mkv", api_key, socket)
    logger.info("Running FFMPEG command..")
    await sender.shell_command("""ffmpeg -y -i "./user_files/debug/test.mkv" -c:v libx264 -profile:v high -vf format=yuv420p -c:a aac -ac 2 -dn -map_metadata:c -1 -map_chapters:c -1 "./user_files/debug/test.mp4" """, api_key, socket)
    await sender.get_file("test.mp4", api_key, socket)
    await sender.shell_command("rm \"./user_files/debug/test.mkv\"", api_key, socket)
    await sender.shell_command("rm \"./user_files/debug/test.mp4\"", api_key, socket)

async def main():
    print("Trying to connect...")
    async with await sender.server_connect(host_url) as socket:
        await do_tasks(socket)

if __name__ == "__main__":
    asyncio.run(main())
