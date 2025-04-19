import requests
import json
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

with open('config.json', 'r') as config_file:
    config = json.load(config_file)

api_key = config['api_key']
url = "https://api.openai.com/v1/images/generations"

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = config['payload']
filename = config['filename']

try:
    response = requests.post(url, headers=headers, json=payload, verify=False)
    response.raise_for_status()

    data = response.json()
    for i, image_info in enumerate(data['data']):
        image_url = image_info['url']
        image_response = requests.get(image_url)

        if image_response.status_code == 200:
            image_filename = f"{filename}{i + 1}.png"
            with open(image_filename, 'wb') as img_file:
                img_file.write(image_response.content)
            print(f"Image saved as {image_filename}")
        else:
            print(f"Failed to download image {i + 1}: {image_response.status_code} {image_response.content}")
except requests.exceptions.RequestException as e:
    print(f"Error: {e}")
    if response is not None:
        print("Response text:", response.text)