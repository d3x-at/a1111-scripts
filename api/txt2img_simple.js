/*
  usage: node txt2img_simple.js
*/
const fs = require('fs');

const url = "http://127.0.0.1:7860"

const payload = {
    "prompt": "puppy dog",
    "steps": 1,
    "batch_size": 2
};

async function main() {
    const response = await fetch(url + "/sdapi/v1/txt2img", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        throw new Error("post request failed")
    }

    const result = await response.json();

    result["images"].forEach((base64_image, i) => {
        let buffer = Buffer.from(base64_image, 'base64')

        fs.writeFile('output' + i + '.png', buffer, err => {
            if (err) {
                console.error(err);
            }
        });
    });
}

main();