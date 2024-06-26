"""
usage: python3 img2img.py <directory> <glob pattern>
i.e.: python3 img2img.py images **/*.png

puts out <original_filename>_img2img.png next to the original file

add more servers to SERVERS to process stuff in parallel
add to or change PAYLOAD to change image generation parameters
"""
import asyncio
import base64
import logging
import sys
from io import BytesIO
from pathlib import Path

from aiofiles import open, ospath
from aiohttp import ClientSession, ClientTimeout
from PIL import Image
from sd_parsers import ParserManager

SERVERS = ["http://127.0.0.1:7860"]

PAYLOAD = {"steps": 5, "denoising_strength": 0.2}

session_timeout = ClientTimeout(total=None, sock_connect=10, sock_read=600)
queue: asyncio.Queue[Path] = asyncio.Queue()
parser = ParserManager()

parse_images = True
"""set to `False` to prevent the script from automatically populating the payload"""


async def worker(server_address):
    """one of these guys is run for each SERVERS entry"""
    async with ClientSession(server_address, timeout=session_timeout) as session:
        while True:
            # get a filename from the queue
            filename = await queue.get()
            try:
                # determine the output filename
                # attention: the API does return the file type set in the backend options
                #   see txt2img.py for one approach of handling this situation
                output_filename = filename.with_stem(filename.stem + "_img2img")
                if await ospath.exists(output_filename):
                    raise ValueError("file already exists", output_filename)

                # prepare the img2img payload
                payload = await get_payload(filename)
                # call the img2img API
                images = await img2img(payload, session)

                # save the output to disk
                image_bytes = base64.b64decode(images[0])
                async with open(output_filename, "wb") as fp:
                    await fp.write(image_bytes)

            except RuntimeError:
                logging.exception("error interrogating file: %s", filename)
            except Exception:
                logging.exception("unexpected error")

            queue.task_done()


async def img2img(payload: dict, session: ClientSession):
    async with session.post("/sdapi/v1/img2img", json=payload) as response:
        if not response.ok:
            raise RuntimeError("error querying server", response.status, await response.text())
        result = await response.json()
    return result["images"]


async def get_payload(image_filename: Path, custom_payload=PAYLOAD):
    """build a payload from a given image and a custom payload"""
    # read image
    async with open(image_filename, mode="rb") as fp:
        image_bytes = await fp.read()

    # get image parameters
    with BytesIO(image_bytes) as buffered, Image.open(buffered) as image:
        mime_type = Image.MIME[image.format]
        image_parameters = get_image_params(image) or {}
        image_parameters.update({"height": image.height, "width": image.width})

    # convert image to something we can POST to A1111
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    return {
        **image_parameters,
        **custom_payload,
        # The A1111 does not need a mime type for now. As we have it though, let's use it!
        "init_images": [f"data:{mime_type};base64,{base64_image}"],
    }


def get_image_params(image):
    """parse image generation parameters from the given image"""
    if not parse_images:
        return None

    image_parameters = parser.parse(image)
    if not image_parameters:
        return None

    params = {}
    prompt = ", ".join(prompt.value for prompt in image_parameters.prompts)
    if prompt:
        params["prompt"] = prompt

    negative_prompt = ", ".join(prompt.value for prompt in image_parameters.negative_prompts)
    if negative_prompt:
        params["negative_prompt"] = negative_prompt

    try:
        sampler = next(iter(image_parameters.samplers))
        params.update(sampler.parameters, sampler_index=sampler.name)
    except StopIteration:
        logging.warning("no sampler found")

    return params


async def run():
    # create worker tasks
    tasks = [asyncio.create_task(worker(server_address)) for server_address in SERVERS]

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
