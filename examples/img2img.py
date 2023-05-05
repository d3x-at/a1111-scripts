'''
usage: python3 img2img.py <directory> <glob pattern>
i.e.: python3 img2img.py images **/*.png

puts out <original_filename>_img2img.png next to the original file

add more servers to SERVERS to process stuff in parallel
add to or change PAYLOAD to change image generation parameters
'''
import asyncio
import base64
import logging
import sys
from io import BytesIO
from pathlib import Path

from aiofiles import open, ospath
from aiohttp import ClientSession, ClientTimeout
from PIL import Image
from sdparsers import ParserManager

SERVERS = ["http://127.0.0.1:7860"]

PAYLOAD = {
    "steps": 5,
    "denoising_strength": 0.2
}

session_timeout = ClientTimeout(total=None, sock_connect=10, sock_read=600)
queue = asyncio.Queue()
parser = ParserManager()


async def worker(server_address, queue):
    async with ClientSession(server_address, timeout=session_timeout) as session:
        while True:
            filename = await queue.get()
            try:
                output_filename = filename.with_stem(filename.stem + "_img2img")
                if await ospath.exists(output_filename):
                    raise ValueError("file already exists", output_filename)

                payload = await get_payload(filename)
                images = await img2img(payload, session)
                await save_output(images[0], output_filename)
            except RuntimeError:
                logging.exception("error interrogating file: %s", filename)
            except Exception:
                logging.exception("unexpected error")
            queue.task_done()


async def img2img(payload: dict, session: ClientSession):
    async with session.post('/sdapi/v1/img2img', json=payload) as response:
        if not response.ok:
            raise RuntimeError("error querying server", response.status, await response.text())
        result = await response.json()
    return result['images']


async def get_payload(image_filename: Path):
    async with open(image_filename, mode='rb') as fp:
        with BytesIO(await fp.read()) as buffered, Image.open(buffered) as image:
            base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
            image_parameters = parser.parse(image)
            mime_type = image.get_format_mimetype()
            payload = {
                'height': image.height,
                'width': image.width
            }

    if image_parameters:
        try:
            prompt, negative_prompt = image_parameters.prompts[0]
            if prompt:
                payload['prompt'] = prompt.value
            if negative_prompt:
                payload['negative_prompt'] = negative_prompt.value
        except KeyError:
            logging.warning("no prompt found in %s", image_filename)
        try:
            sampler = image_parameters.samplers[0]
            payload.update(sampler.parameters, sampler_index=sampler.name)
        except KeyError:
            logging.warning("no sampler found in %s", image_filename)

    return {
        **payload,
        **PAYLOAD,
        "init_images": [f"data:{mime_type};base64,{base64_image}"]
    }


async def save_output(base64_image: str, filename: Path):
    image_bytes = base64.b64decode(base64_image)
    async with open(filename, 'wb') as fp:
        await fp.write(image_bytes)


def add_files(directory, glob_pattern):
    dir_path = Path(directory)
    if not dir_path.exists():
        raise ValueError("directory does not exist")

    for filename in dir_path.glob(glob_pattern):
        queue.put_nowait(filename)


async def run():
    tasks = []
    for server_address in SERVERS:
        task = asyncio.create_task(worker(server_address, queue))
        tasks.append(task)

    await queue.join()

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)


async def main(directory, glob_pattern):
    add_files(directory, glob_pattern)
    await run()


if __name__ == "__main__":
    try:
        asyncio.run(main(*sys.argv[1:3]))
    except TypeError as error:
        print(str(error))
