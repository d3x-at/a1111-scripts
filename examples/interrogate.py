'''
usage: python3 interrogate.py <directory> <glob pattern>
i.e.: python3 interrogate.py images **/*.png

puts out <original_filename>.txt next to the original file

add more servers to SERVERS to process stuff in parallel
'''
import asyncio
import base64
import logging
import sys
from pathlib import Path

from aiofiles import open, ospath
from aiohttp import ClientSession, ClientTimeout

SERVERS = ["http://127.0.0.1:7860"]

MODEL = "clip"

session_timeout = ClientTimeout(total=None, sock_connect=10, sock_read=600)
queue = asyncio.Queue()


async def worker(server_address):
    '''one of these guys is run for each SERVERS entry'''
    async with ClientSession(server_address, timeout=session_timeout) as session:
        while True:
            # get a filename from the queue
            filename = await queue.get()
            try:
                # determine the output filename
                output_filename = filename.with_suffix('.txt')
                if await ospath.exists(output_filename):
                    raise ValueError("file already exists", output_filename)

                # prepare the img2img payload
                payload = await get_payload(filename)
                # call the interrogate API
                caption = await interrogate(payload, session)

                # save the output to disk
                async with open(output_filename, 'w', encoding='utf-8') as fp:
                    await fp.write(caption)

            except RuntimeError:
                logging.exception("error interrogating file: %s", filename)
            except Exception:
                logging.exception("unexpected error")

            queue.task_done()


async def interrogate(payload: dict, session: ClientSession):
    async with session.post('/sdapi/v1/interrogate', json=payload) as response:
        if not response.ok:
            raise RuntimeError("error querying server", response.status, await response.text())
        result = await response.json()
    return result['caption']


async def get_payload(image_filename: Path):
    '''build a payload from given image'''
    # read image & convert to base64 encoded string
    async with open(image_filename, mode='rb') as fp:
        base64_image = base64.b64encode(await fp.read()).decode('utf-8')

    # assemble payload
    return {
        "image": base64_image,
        "model": MODEL
    }


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


async def main(directory, glob_pattern):
    dir_path = Path(directory)
    if not dir_path.exists():
        raise ValueError("directory does not exist")

    for filename in dir_path.glob(glob_pattern):
        queue.put_nowait(filename)

    await run()


if __name__ == "__main__":
    try:
        asyncio.run(main(*sys.argv[1:3]))
    except TypeError as error:
        print(str(error))
