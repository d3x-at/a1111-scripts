Basic scripts to process loads of images using the A1111 API.

The scripts need one (or more) running instance(s) of the [Stable Diffusion WebUI](https://github.com/AUTOMATIC1111/stable-diffusion-webui) to connect to.

* [txt2img_simple.py](api/txt2img_simple.py), [txt2img_simple.js](api/txt2img_simple.js)

  Basic Text 2 Image examples.
  
  Request a single image generation.

* [txt2img.py](api/txt2img.py)

  Batch Text 2 Image example.
  
  Generates a number of images with a given prompt (and other parameters).
  
  Uses multiple backend servers for generation, if given.

* [interrogate.py](api/interrogate.py)

  Batch Interrogation example.

  Iterates over a list of image files, writes text file with interrogated captions.

  Uses multiple backend servers for generation, if given.

* [img2img.py](api/img2img.py)

  Batch Image 2 Image example using the [sd-parsers](https://github.com/d3x-at/sd-parsers) library.
  
  Iterates over a list of image files, reuses previous & injects custom generation parameters.
  
  Uses multiple backend servers for generation, if given.

* [img2vid.py](api/img2vid.py)

  Batch Image 2 Image 2 Video using the [ffmpeg-python](https://github.com/kkroening/ffmpeg-python) library.
  
  Similar to [img2img.py](api/img2img.py) but creates a video file instead.

  Allows the use of the built-in ffmpeg filters on the output video.

  Uses multiple backend servers for generation, if given.

* [vid2vid_simple.py](api/vid2vid_simple.py)

  Basic video 2 video script using the [imageio](https://github.com/imageio/imageio) library.

  Processes each frame of an input video using the Img2Img API, builds a new video as result.

* [vid2vid_ffmpeg.py](api/vid2vid_ffmpeg.py)

  Basic video 2 video script using the [ffmpeg-python](https://github.com/kkroening/ffmpeg-python) library.

  Allows the use of the built-in ffmpeg filters on the output video.

  Processes each frame of an input video using the Img2Img API, builds a new video as result.

* [webcam.py](api/webcam.py)

  Process live webcam footage using the [pygame](https://github.com/pygame/pygame) library.
  
  Grabs frames from a webcam and processes them using the Img2Img API, displays the resulting images.