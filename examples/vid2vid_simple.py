'''
usage: python3 vid2vid_simple.py input.mp4 output.mp4

add to or change PAYLOAD to change image generation parameters
'''
import base64
import sys

import imageio.v3 as iio
import requests

URL = "http://127.0.0.1:7860"

PAYLOAD = {
    "prompt": "puppy dog",
    "steps": 20,
    "denoising_strength": 0.2
}


def img2img(frame):
    # convert frame to a base 64 encoded image
    input_bytes = iio.imwrite("<bytes>", frame, extension=".png")
    base64_image = base64.b64encode(input_bytes).decode('utf-8')

    # default height and width for img2img
    width, height, _ = frame.shape

    # assemble payload
    payload = {
        'width': width,
        'height': height,
        **PAYLOAD,
        "init_images": [base64_image]
    }

    # call img2img API
    response = requests.post(f'{URL}/sdapi/v1/img2img', json=payload)
    if not response.ok:
        raise RuntimeError("post request failed")

    result = response.json()
    output_bytes = base64.b64decode(result['images'][0])

    # return the img2img result as ndarray
    return iio.imread(output_bytes)


def main(input_file, output_file):
    # get fps from original video (default to 24 if not found)
    fps = int(iio.immeta(input_file, plugin="pyav").get('fps', 24))

    # open the output file for writing
    with iio.imopen(output_file, "w", plugin="pyav") as output:
        # initialize new output video stream
        output.init_video_stream("libx264", fps=fps)

        # iterate over frames of input file
        for frame in iio.imiter(input_file, plugin="pyav"):
            # send to img2img
            frame = img2img(frame)
            # add to output video
            output.write_frame(frame)


if __name__ == "__main__":
    try:
        main(*sys.argv[1:3])
    except TypeError as error:
        print(str(error))
