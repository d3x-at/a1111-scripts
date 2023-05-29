'''
usage: python3 webcam.py
'''
import base64
import sys
from io import BytesIO

import pygame.camera
import pygame.image
import requests

URL = "http://127.0.0.1:7860"

PAYLOAD = {
    "prompt": "a puppy dog",
    "steps": 5,
    "denoising_strength": 0.2
}

# The camera to use
CAMERA_INDEX = 0

# The resolution to request from the camera
CAMERA_RESOLUTION = (640, 480)

# Set to True to send frames to the img2img api
DO_IMG2IMG = False


def to_base64(frame):
    # convert frame surface to base64 encoded PNG
    with BytesIO() as buffer:
        pygame.image.save(frame, buffer, "img.png")
        return base64.b64encode(buffer.getvalue()).decode('utf-8')


def from_base64(base64_image):
    with BytesIO(base64.b64decode(base64_image)) as buffer:
        return pygame.image.load(buffer)


class Game:
    def __init__(self):
        pygame.camera.init()
        cameras = pygame.camera.list_cameras()

        print(f"Using camera {cameras[CAMERA_INDEX]}")
        self.webcam = pygame.camera.Camera(cameras[CAMERA_INDEX], CAMERA_RESOLUTION)
        self.webcam.start()

        frame = self.webcam.get_image()
        self.frame_width = frame.get_width()
        self.frame_height = frame.get_height()
        self.screen = pygame.display.set_mode((self.frame_width, self.frame_height))

        pygame.display.set_caption("pyGame Camera View")

    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    sys.exit()
            # grab frame
            frame = self.webcam.get_image()
            # process frame with img2img
            if DO_IMG2IMG:
                frame = self.img2img(frame)
            # draw frame
            self.screen.blit(frame, (0, 0))
            # update display
            pygame.display.flip()

    def img2img(self, frame: pygame.Surface):
        base64_image = to_base64(frame)

        # assemble payload
        payload = {
            'width': self.frame_width,
            'height': self.frame_height,
            **PAYLOAD,
            "init_images": [base64_image]
        }

        # call img2img API
        response = requests.post(f'{URL}/sdapi/v1/img2img', json=payload)
        if not response.ok:
            raise RuntimeError("post request failed")

        result = response.json()
        return from_base64(result['images'][0])


if __name__ == "__main__":
    Game().run()
