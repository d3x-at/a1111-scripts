'''
usage: python3 webcam.py
'''
import base64
from io import BytesIO
from threading import Thread

import pygame.camera
import pygame.image
import requests

URL = "http://127.0.0.1:7860"

PAYLOAD = {
    "prompt": "a puppy dog",
    "steps": 15,
    "denoising_strength": 0.75
}

# Set to True to send frames to the img2img api
DO_IMG2IMG = False

# Save img2img frames to disk
SAVE_FRAMES = False

# The camera to use
CAMERA_INDEX = 0

# The resolution to request from the camera
CAMERA_RESOLUTION = (640, 480)

# Set crop dimensions (x, y, width, height) to crop the camera image
# e.g.: CAMERA_CROP = (100, 0, 384, 512)
CAMERA_CROP = None


def to_base64(frame):
    # convert frame surface to base64 encoded PNG
    with BytesIO() as buffer:
        pygame.image.save(frame, buffer, "img.png")
        return base64.b64encode(buffer.getvalue()).decode('utf-8')


def from_base64(base64_image, frame_no: int, save_to_disk: bool = False):
    with BytesIO(base64.b64decode(base64_image)) as buffer:
        if save_to_disk:
            with open(f"{frame_no:08d}.png", "wb") as fp:
                fp.write(buffer.getbuffer())
        return pygame.image.load(buffer)


class Game:
    run = True
    crop = None
    frame_no = 0

    @property
    def width(self):
        return self.crop[2] if self.crop else self.frame_width

    @property
    def height(self):
        return self.crop[3] if self.crop else self.frame_height

    def __init__(self):
        pygame.camera.init()
        cameras = pygame.camera.list_cameras()

        print(f"Using camera {cameras[CAMERA_INDEX]}")
        self.webcam = pygame.camera.Camera(cameras[CAMERA_INDEX], CAMERA_RESOLUTION)
        self.webcam.start()

        frame = self.webcam.get_image()
        self.frame_width = frame.get_width()
        self.frame_height = frame.get_height()

        if CAMERA_CROP:
            x, y, width, height = CAMERA_CROP
            width = min(width, self.frame_width)
            height = min(height, self.frame_height)
            x = min(x, self.frame_width - width)
            y = min(y, self.frame_height - height)
            self.crop = (x, y, width, height)

        self.screen = pygame.display.set_mode((self.width, self.height))

        print(f"Resolution: {self.frame_width}x{self.frame_height}")
        if self.crop:
            print(f"Crop to: {self.crop}")

        pygame.display.set_caption("pyGame Camera View")

    def run(self):
        t = Thread(target=self.process)
        t.start()

        while t.is_alive():
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.run = False

            t.join(.01)

    def process(self):
        while self.run:
            self.frame_no += 1

            # grab frame
            frame = self.webcam.get_image()

            # crop
            if self.crop:
                frame = frame.subsurface(self.crop)

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
            'width': self.width,
            'height': self.height,
            **PAYLOAD,
            'init_images': [base64_image],
            'alwayson_scripts': {
                'controlnet': {'args': [
                    {
                        "module": "depth_midas",
                        "model": "control_v11f1p_sd15_depth [cfd03158]",
                        "control_mode": 0,
                        "weight": 0.5,
                        "input_image": base64_image,
                    },
                    {
                        "module": "canny",
                        "model": "control_v11p_sd15_canny [d14c016b]",
                        "control_mode": 0,
                        "weight": 0.5,
                        "input_image": base64_image,
                    }
                ]}
            }
        }

        # call img2img API
        response = requests.post(f'{URL}/sdapi/v1/img2img', json=payload)
        if not response.ok:
            raise RuntimeError("post request failed")

        result = response.json()
        return from_base64(result['images'][0], self.frame_no, SAVE_FRAMES)


if __name__ == "__main__":
    Game().run()
