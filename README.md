Basic scripts to process loads of images using the A1111 API.

* [txt2img_simple.py](api/txt2img_simple.py), [txt2img_simple.js](api/txt2img_simple.js)

  Basic Text 2 Image examples.
  
  Request a single image generation.

* [txt2img.py](api/txt2img.py)

  Batch Text 2 Image example.
  
  Iterates over a number of given prompts.
  
  Uses multiple backend servers for generation, if given.

* [interrogate.py](api/interrogate.py)

  Batch Interrogation example.

  Iterates over a list of image files, writes text file with interrogated captions.

  Uses multiple backend servers for generation, if given.

* [img2img.py](api/img2img.py)

  Batch Image 2 Image example using the [sd-parsers](https://github.com/d3x-at/sd-parsers) library.
  
  Iterates over a list of image files, reuses previous & injects custom generation parameters.
  
  Uses multiple backend servers for generation, if given.

* [vid2vid_simple.py](api/vid2vid_simple.py)

  Basic video 2 video script using the [imageio](https://github.com/imageio/imageio) library.

  Processes each frame of an input video using the Img2Img API, builds a new video as result.

  Not too useful for the time being, use TemporalKit, EbSynth or similar to produce good-looking stuff.

* [img2vid.py](api/img2vid.py)

  Batch Image 2 Image 2 Video using the [ffmpeg-python](https://github.com/kkroening/ffmpeg-python) library.
  
  Similar to [img2img.py](api/img2img.py) but creates a video file instead.

  Uses multiple backend servers for generation, if given.