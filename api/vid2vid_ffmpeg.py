'''
usage: python3 vid2vid_ffmpeg.py input.mp4 output.mp4

add to or change PAYLOAD to change image generation parameters

a call for TemporalNet is prepared below (line 80+), uncomment if needed

'''
import base64
import contextlib
import sys
from io import BytesIO

import ffmpeg
import numpy as np
import requests
from PIL import Image

URL = "http://127.0.0.1:7860"

PAYLOAD = {
    "prompt": "a cute puppy dog",
    "steps": 15,
    "denoising_strength": 0.20,
    'seed': 123,
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
    # 'minterpolate': {
    #    'fps': 24,
    #    'mi_mode': "mci",
    #    'mc_mode': "aobmc",
    #    'me_mode': "bidir",
    #    'vsbmc': 1
    # }
}


def img2img(frame: bytes, payload_base: dict, context: dict) -> bytes:
    base64_frame = base64.b64encode(frame).decode('utf-8')

    # assemble payload
    payload = {
        **payload_base,
        "init_images": [base64_frame]
    }

    # add controlnets
    payload["alwayson_scripts"]["controlnet"] = {"args": [
        # {
        #    "module": "reference_only",
        #    "input_image": base64_frame
        # },
        {
            "module": "canny",
            "model": "control_canny-fp16 [e3fe7712]",
            "control_mode": 2,
            "input_image": base64_frame,
        }
    ]}

    # add temporalnet if we have a previous image
    # last_generated = context.get('last_generated')
    # if last_generated is not None:
    #     payload["alwayson_scripts"]["controlnet"]["args"].append({
    #         "input_image": last_generated,
    #         "model": "diff_control_sd15_temporalnet_fp16 [adc6bd97]",
    #         "module": "none",
    #         "weight": 0.7,
    #         "guidance": 1,
    #     })

    # call img2img API
    response = requests.post(f'{URL}/sdapi/v1/img2img', json=payload)
    if not response.ok:
        raise RuntimeError("post request failed")

    base64_image = response.json()['images'][0]
    context['last_source_image'] = base64_frame
    context['last_generated'] = base64_image

    return base64.b64decode(base64_image)


def read_frames(input_file, r_frames, width, height):
    input_process = (
        ffmpeg
        .input(input_file, loglevel='quiet')
        .output('pipe:', format='rawvideo', pix_fmt='rgb24', r=r_frames)
        .run_async(pipe_stdout=True)
    )

    try:
        while True:
            in_bytes = input_process.stdout.read(width * height * 3)
            if not in_bytes:
                break

            frame = np.frombuffer(in_bytes, np.uint8).reshape([height, width, 3])

            with Image.fromarray(frame, mode="RGB") as image, BytesIO() as buffer:
                image.save(buffer, "PNG")
                yield buffer.getvalue()

    finally:
        input_process.stdout.close()
        input_process.wait()


@contextlib.contextmanager
def prepare_output(output_file: str, frame_rate):
    frames_input = ffmpeg.input('pipe:', format='image2pipe', framerate=frame_rate)

    # filters
    for name, params in FFMPEG_FILTERS.items():
        frames_input = frames_input.filter(name, **params)

    ffmpeg_process = (
        frames_input
        .output(output_file, **FFMPEG_OUTPUT_PARAMS)
        .run_async(pipe_stdin=True)
    )

    try:
        yield ffmpeg_process
    finally:
        ffmpeg_process.stdin.close()
        ffmpeg_process.wait()


def probe(filename: str):
    probe = ffmpeg.probe(filename)
    stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'))
    return stream['width'], stream['height'], stream['r_frame_rate']


def main(input_file: str, output_file: str):
    width, height, r_frames = probe(input_file)
    payload_base = {
        'width': width,
        'height': height,
        'alwayson_scripts': {},
        **PAYLOAD
    }

    img2img_context = {}
    with prepare_output(output_file, r_frames) as output:
        for frame in read_frames(input_file, r_frames, width, height):
            output.stdin.write(img2img(frame, payload_base, img2img_context))


if __name__ == "__main__":
    try:
        main(*sys.argv[1:3])
    except TypeError as error:
        print(str(error))
