'''
usage: python3 txt2img_simple.py
'''
import base64
import requests

url = "http://127.0.0.1:7860"

payload = {
    "prompt": "puppy dog",
    "steps": 5,
    "batch_size": 2
}

# request the image generation from the backend
response = requests.post(f'{url}/sdapi/v1/txt2img', json=payload)
if not response.ok:
    raise RuntimeError("post request failed")

# write each file to disk
for i, base64_image in enumerate(response.json()['images']):
    # attention: the API does return the file type set in the backend options
    #   trusting it to be always png will go wrong eventually
    with open(f'output{i}.png', 'wb') as fp:
        fp.write(base64.b64decode(base64_image))
