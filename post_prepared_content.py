import os
import json
import csv
import requests

# Load secrets
with open("config/secrets.json", "r") as f:
    secrets = json.load(f)

ACCESS_TOKEN = secrets["access_token"]
IG_USER_ID = secrets["ig_user_id"]
ENCODING = "latin-1"

BASE_IMAGE_URL = secrets["base-url"]

def build_image_url(filename):
    return f"{BASE_IMAGE_URL}/{filename}"

def post_images_from_folder(folder_path, caption):
    image_files = sorted([
        file for file in os.listdir(folder_path)
        if file.lower().endswith(('.jpg', '.jpeg', '.png'))
    ])

    if not image_files:
        raise ValueError(f"No images found in folder: {folder_path}")

    media_ids = []

    if len(image_files) == 1:
        image_url = build_image_url(image_files[0])
        res = requests.post(
            f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
            params={
                "image_url": image_url,
                "caption": caption,
                "access_token": ACCESS_TOKEN
            }
        )
        container = res.json()
        if "id" not in container:
            raise Exception(f"Failed to create container: {container}")

        publish_res = requests.post(
            f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish",
            params={
                "creation_id": container["id"],
                "access_token": ACCESS_TOKEN
            }
        )
        print("✅ Posted single image:", publish_res.json())

    else:
        for img_name in image_files:
            image_url = build_image_url(img_name)
            res = requests.post(
                f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
                params={
                    "image_url": image_url,
                    "is_carousel_item": "true",
                    "access_token": ACCESS_TOKEN
                }
            )
            media_id = res.json().get("id")
            if not media_id:
                raise Exception(f"Failed to upload image: {res.json()}")
            media_ids.append(media_id)

        carousel_res = requests.post(
            f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
            params={
                "children": media_ids,
                "media_type": "CAROUSEL",
                "caption": caption,
                "access_token": ACCESS_TOKEN
            }
        )

        carousel_id = carousel_res.json().get("id")
        if not carousel_id:
            raise Exception(f"Failed to create carousel: {carousel_res.json()}")

        publish_res = requests.post(
            f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish",
            params={
                "creation_id": carousel_id,
                "access_token": ACCESS_TOKEN
            }
        )
        print("✅ Posted carousel:", publish_res.json())

def main():
    with open("data/product_list.csv", "r", encoding=ENCODING) as f:
        product_data = list(csv.DictReader(f, delimiter=';'))

    folders = os.listdir("output")
    for folder in folders:
        folder_path = os.path.join("output", folder)
        if not os.path.isdir(folder_path):
            continue

        caption_path = os.path.join(folder_path, "caption.txt")
        if not os.path.exists(caption_path):
            print(f"⚠️ Caption missing for: {folder}")
            continue

        with open(caption_path, "r", encoding="utf-8") as f:
            caption = f.read().strip()

        try:
            post_images_from_folder(folder_path, caption)
            break  # Only one post per run
        except Exception as e:
            print(f"❌ Failed to post from {folder}: {e}")
            continue

if __name__ == "__main__":
    main()