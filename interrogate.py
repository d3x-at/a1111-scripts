'''
usage: python3 interrogate.py <directory> <glob pattern>
i.e.: python3 interrogate.py images **/*.png
'''
import asyncio
import base64
import logging
import sys
from io import BytesIO
from pathlib import Path

from aiohttp import ClientSession
from PIL import Image

SERVERS = ["http://127.0.0.1:7860"]


async def worker(server_address, queue, model: str = "clip"):
    async with ClientSession(server_address) as session:
        while True:
            image_filename = await queue.get()
            try:
                await interrogate_file(image_filename, model, session)
            except RuntimeError:
                logging.warning("error interrogating file: %s", image_filename)
            except Exception:
                logging.exception("unexpected error")
            queue.task_done()


async def interrogate_file(filename: Path, model: str, session: ClientSession):
    output_file = filename.with_suffix('.txt')
    if output_file.exists():
        raise RuntimeError("file already exists", filename)

    payload = get_payload(filename, model)

    async with session.post('/sdapi/v1/interrogate', json=payload) as response:
        if not response.ok:
            raise RuntimeError("error querying server", response.status, await response.text())
        caption = (await response.json()).get('caption')

    if not caption:
        raise RuntimeError('caption is empty')

    write_file_caption(caption, output_file)


def get_payload(image_filename: Path, model: str):
    with Image.open(image_filename) as image, BytesIO() as buffered:
        mime_type = image.get_format_mimetype()
        image.save(buffered, format=image.format)
        base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')

    return {
        "image": f"data:{mime_type};base64,{base64_image}",
        "model": model
    }


def write_file_caption(caption: str, file_path: Path):
    with open(file_path, 'w', encoding='utf-8') as fp:
        fp.write(caption)


async def main(directory, glob_pattern):
    dir_path = Path(directory)
    if not dir_path.exists():
        raise ValueError("directory does not exist")

    queue = asyncio.Queue()
    for filename in dir_path.glob(glob_pattern):
        queue.put_nowait(filename)

    tasks = []
    for server_address in SERVERS:
        task = asyncio.create_task(worker(server_address, queue))
        tasks.append(task)

    await queue.join()

    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    try:
        asyncio.run(main(*sys.argv[1:3]))
    except TypeError as error:
        print(str(error))
