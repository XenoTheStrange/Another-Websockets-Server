#!/usr/bin/python3
import sys
import asyncio
#import py script from another directory by adding it to the system path
sys.path.append("./sender")
import sender


host_url = "wss://192.168.1.31:6789"
api_key = "0xDEADBEEF"

"""Edit this function to start the tasks you need"""
async def start_tasks(socket):
    names = [
        "ffmpeg_task"
        ]
    await sender.send_file("./test.mkv", api_key, socket)
    await sender.shell_command(["ffmpeg", "-y", "-i", "./user_files/debug/test.mkv", "-c:v", "libx264", "-profile:v", "high", "-vf", "format=yuv420p", "-c:a", "aac", "-ac", "2", "-dn", "-map_metadata:c", "-1", "-map_chapters:c", "-1", "./user_files/debug/test.mp4"], api_key, socket, task=True, name=names[0])
    return names

async def do_after_tasks(socket):
    await sender.get_file("test.mp4", api_key, socket)
    await sender.shell_command(["rm", "./user_files/debug/test.mkv"], api_key, socket)
    await sender.shell_command(["rm", "./user_files/debug/test.mp4"], api_key, socket)
    print("files cleaned up")

async def main():
    async with await sender.server_connect(host_url) as socket:
        #Start all the tasks that you defined
        tasks = await start_tasks(socket)
        print("Tasks have been started")
        completed_tasks = set()
        while True:
            for task in tasks:
                if task in completed_tasks:
                    continue
                response = await sender.check_task(task, api_key, socket)
                if "still running" not in response:
                    completed_tasks.add(task)
                    print(f"Task finished: {task}")
                    print(f"Response: {response}")
            
            if len(completed_tasks) ==  len(tasks):
                print("All tasks finished")
                await do_after_tasks(socket)
                break
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
