'''
Usage: python3 img2vid.py <directory> <glob pattern> <output file name>
i.e.: python3 img2vid.py images "**/*.png" output.mp4

Needs img2img.py next to it.
Needs ffmpeg.

add more servers to SERVERS to process stuff in parallel
add to or change PAYLOAD to change image generation parameters

edit FFMPEG_INPUT_PARAMS, FFMPEG_OUTPUT_PARAMS and FFMPEG_FILTERS to influence the video creation process
'''
import asyncio
import base64
import contextlib
import sys
from pathlib import Path

import ffmpeg
import img2img
from aiohttp import ClientSession, ClientTimeout

SERVERS = ["http://127.0.0.1:7860"]

PAYLOAD = {
    "steps": 30,
    "denoising_strength": 0.2
}

FFMPEG_INPUT_PARAMS = {
    'framerate': 12
}

FFMPEG_OUTPUT_PARAMS = {
    'vcodec': 'libx264',
    'crf': 23
}

FFMPEG_FILTERS = {
    # Add as many (or as little) filters as you want.
    # Order matters!
    #
    # time blend - https://ffmpeg.org/ffmpeg-filters.html#blend-1
    # 'tblend': {
    #    'all_mode': 'average'
    # },
    # deflicker - https://ffmpeg.org/ffmpeg-filters.html#deflicker
    # 'deflicker': {
    #    'mode': 'pm',
    #    'size': 5
    # },
    # minterpolate - https://ffmpeg.org/ffmpeg-filters.html#minterpolate
    'minterpolate': {
        'fps': 24,
        'mi_mode': "mci",
        'mc_mode': "aobmc",
        'me_mode': "bidir",
        'vsbmc': 1
    }
}

session_timeout = ClientTimeout(total=None, sock_connect=10, sock_read=600)
queue = asyncio.Queue()


async def ffmpeg_worker(ffmpeg_process):
    async def async_write(process, image: bytes):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, process.stdin.write, image)

    while True:
        image = await queue.get()
        await async_write(ffmpeg_process, image)
        queue.task_done()


def init_ffmpeg(output_filename: str, overwrite_output: bool = True):
    # input
    input = ffmpeg.input('pipe:', format='image2pipe', **FFMPEG_INPUT_PARAMS)

    # filters
    for name, params in FFMPEG_FILTERS.items():
        input = input.filter(name, **params)

    # output
    out = input.output(output_filename, **FFMPEG_OUTPUT_PARAMS)
    if overwrite_output:
        out = out.overwrite_output()

    # run ffmpeg process
    return out.run_async(pipe_stdin=True)


async def get_image(session, filename) -> bytes:
    payload = await img2img.get_payload(filename, custom_payload=PAYLOAD)
    images = await img2img.img2img(payload, session)
    return base64.b64decode(images[0])


@contextlib.asynccontextmanager
async def init_sessions():
    sessions = []
    for server_address in SERVERS:
        sessions.append(ClientSession(server_address, timeout=session_timeout))
    try:
        yield sessions
    finally:
        await asyncio.gather(*(session.close() for session in sessions))
        await asyncio.sleep(0)


async def main(directory, glob_pattern, output_filename):
    async def collect_tasks():
        nonlocal tasks
        images = await asyncio.gather(*tasks, return_exceptions=True)
        tasks = []
        for image in images:
            queue.put_nowait(image)

    process = init_ffmpeg(output_filename)
    ffmpeg_task = asyncio.create_task(ffmpeg_worker(process))
    tasks = []

    async with init_sessions() as sessions:
        num_sessions = len(sessions)

        for index, filename in enumerate(Path(directory).glob(glob_pattern)):
            session = sessions[index % num_sessions]
            task = asyncio.create_task(get_image(session, filename))
            tasks.append(task)

            if len(tasks) == num_sessions:
                await collect_tasks()

    if tasks:
        await collect_tasks()

    await queue.join()
    ffmpeg_task.cancel()
    await asyncio.gather(ffmpeg_task, return_exceptions=True)

    process.stdin.close()
    process.wait()


if __name__ == "__main__":
    try:
        asyncio.run(main(*sys.argv[1:4]))
    except TypeError as error:
        print(str(error))
