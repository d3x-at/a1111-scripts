#!/usr/bin/env python3
'''
usage: python3 txt2img.py "a puppy dog"
get help with: python3 txt2img.py -h
'''
import argparse
import asyncio
import base64
import logging
from itertools import count
from pathlib import Path

from aiofiles import open, ospath
from aiohttp import ClientSession, ClientTimeout

OUTPUT_FOLDER = "."
SERVERS = ["http://127.0.0.1:7860"]

JPG_SIG = bytes.fromhex("ff d8 ff")
PNG_SIG = bytes.fromhex("89 50  4e  47  0d  0a  1a  0a")

session_timeout = ClientTimeout(total=None, sock_connect=10, sock_read=600)
queue = asyncio.Queue()


async def worker(server_address):
    async with ClientSession(server_address, timeout=session_timeout) as session:
        while True:
            # get job id and payload from the queue
            index, payload = await queue.get()
            try:
                # request image generation, loop over resulting images
                for base64_image in await txt2img(payload, session):
                    image_bytes = base64.b64decode(base64_image)

                    # save image to disk
                    output_filename = await get_filename(image_bytes, index)
                    async with open(output_filename, 'wb') as fp:
                        await fp.write(image_bytes)

            except RuntimeError:
                logging.exception("error generating image")
            except Exception:
                logging.exception("unexpected error")

            queue.task_done()


async def txt2img(payload: dict, session: ClientSession):
    async with session.post('/sdapi/v1/txt2img', json=payload) as response:
        if not response.ok:
            raise RuntimeError("error querying server", response.status, await response.text())
        result = await response.json()
    return result['images']


async def get_filename(image_bytes: bytes, index: int):
    # determine image mime type
    if image_bytes.startswith(JPG_SIG):
        extension = ".jpg"
    elif image_bytes.startswith(PNG_SIG):
        extension = ".png"
    else:
        raise RuntimeError("unknown file type")

    # find a "free" filename
    output_folder = Path(OUTPUT_FOLDER)
    filename = output_folder / f"{index:08d}{extension}"
    if not await ospath.exists(filename):
        return filename

    for i in count():
        filename = output_folder / f"{index:08d}_{i:02d}{extension}"
        if not await ospath.exists(filename):
            return filename


async def run():
    # create worker tasks
    tasks = [asyncio.create_task(worker(server_address))
             for server_address in SERVERS]

    # wait for all files to be processed
    await queue.join()

    # shut down workers
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)


async def main():
    # build command line argument parser
    parser = argparse.ArgumentParser(argument_default=argparse.SUPPRESS)
    parser.add_argument('prompt', type=str, help="prompt")
    parser.add_argument('-n', '--negative', type=str, dest='negative_prompt', help="negative prompt")
    parser.add_argument('-c', '--count', type=int, default=1, help="number of generated images")
    parser.add_argument('-s', '--steps', type=int, default=20, help="generation steps")
    parser.add_argument('--width', type=int, help="image width")
    parser.add_argument('--height', type=int, help="image height")
    parser.add_argument('--seed', type=int, help="seed")
    parser.add_argument('--cfg', type=int, dest="cfg_scale", help="cfg scale")
    parser.add_argument('--sampler', type=str, dest="sampler_name", help="sampler name")

    # parse command arguments
    args = parser.parse_args()

    # build job queue
    params = {k: v for k, v in vars(args).items() if k != 'count'}
    for i in range(0, args.count):
        queue.put_nowait((i, {**params}))

    await run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        print(str(error))
