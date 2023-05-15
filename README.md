Basic scripts to process loads of images using the A1111 API.

Example scripts:
* [txt2img_simple.py](examples/txt2img_simple.py), [txt2img_simple.js](examples/txt2img_simple.js)

  Basic Text 2 Image example, requests a single image generation.

* [txt2img.py](examples/txt2img.py)

  Batch Text 2 Image example, iterates over a number of given prompts.
  
  Uses multiple backend servers for generation, if given.

* [img2img.py](examples/img2img.py)

  Batch Image 2 Image example, iterates over a list of image files, injects custom generation parameters.
  
  Uses multiple backend servers for generation, if given.

* [interrogate.py](examples/interrogate.py)

  Batch Interrogation example, iterates over a list of image files.

  Uses multiple backend servers for generation, if given.

* [img2vid.py](examples/img2vid.py)

  Batch Image 2 Image 2 Video, similar to [img2img.py](examples/img2img.py) but creates a video file instead.

  Uses multiple backend servers for generation, if given.