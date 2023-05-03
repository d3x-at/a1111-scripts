'''
usage: python3 txt2img.py
'''
import asyncio
import base64
import logging
from itertools import count
from pathlib import Path

from aiohttp import ClientSession, ClientTimeout

OUTPUT_FOLDER = "tmp"
SERVERS = ["http://127.0.0.1:7860"]

JPG_SIG = bytes.fromhex("ff d8 ff")
PNG_SIG = bytes.fromhex("89 50  4e  47  0d  0a  1a  0a")

session_timeout = ClientTimeout(total=None, sock_connect=10, sock_read=600)
queue = asyncio.Queue()


async def worker(server_address, queue):
    async with ClientSession(server_address, timeout=session_timeout) as session:
        while True:
            payload = await queue.get()
            try:
                await request_image_generation(payload, session)
            except RuntimeError:
                logging.exception("error generating image")
            except Exception:
                logging.exception("unexpected error")
            queue.task_done()


async def request_image_generation(payload: dict, session: ClientSession):
    async with session.post('/sdapi/v1/txt2img', json=payload) as response:
        if not response.ok:
            raise RuntimeError("error querying server", response.status, await response.text())
        r = await response.json()
    for image in r.get('images', []):
        save_output(image)


def save_output(base64_image: str):
    image_bytes = base64.b64decode(base64_image)
    output_filename = get_filename(image_bytes)
    with open(output_filename, 'wb') as fp:
        fp.write(image_bytes)


def get_filename(image_bytes: bytes):

    if image_bytes.startswith(JPG_SIG):
        extension = ".jpg"
    elif image_bytes.startswith(PNG_SIG):
        extension = ".png"
    else:
        raise RuntimeError("unknown file type")

    output_folder = Path(OUTPUT_FOLDER)
    for i in count():
        filename = output_folder / f"{i:08d}{extension}"
        if not filename.exists():
            return filename


def add_prompt(**kwargs):
    queue.put_nowait({**kwargs})


async def run():
    tasks = []
    for server_address in SERVERS:
        task = asyncio.create_task(worker(server_address, queue))
        tasks.append(task)

    await queue.join()

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)


async def main():
    add_prompt(prompt="puppy dog", negative_prompt="cats", steps=5, width=384)
    await run()


if __name__ == "__main__":
    asyncio.run(main())
