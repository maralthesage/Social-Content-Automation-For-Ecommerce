import pandas as pd
import re
import urllib.parse
import requests
import json
import time
import os
from datetime import datetime
from prefect import flow

import ollama

# ========== Config ==========

ENCODING = "utf-8"
LOG_PATH = "data/posted_log.csv"
SECRETS_PATH = "config/secrets.json"
REZEPT_IDS = ["944", "459", "574", "610", "513"]  # full list here

# ========== Load Secrets ==========

with open(SECRETS_PATH, "r", encoding=ENCODING) as f:
    secrets = json.load(f)

ACCESS_TOKEN = secrets["access_token"]
IG_USER_ID = secrets["ig_user_id"]
APPROVALS_XLSX = secrets["sharepoint"]

# ========== Helper Functions ==========

def normalize_german_url(url):
    replacements = {
        "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
        "Ä": "Ae", "Ö": "Oe", "Ü": "Ue"
    }
    parts = url.split("/")
    filename = urllib.parse.unquote(parts[-1])
    for german_char, ascii_replacement in replacements.items():
        filename = filename.replace(german_char, ascii_replacement)
    parts[-1] = filename.lower()
    return "/".join(parts)

def clean_ingredients_from_html(html):
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", html)
    text = re.sub(r"\r\n", "\n", text)
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"&nbsp;", "", text)
    return text.strip()

def create_prompt(recipe_name, ingredients_text, recipe_id):
    return f"""Schreibe eine Instagram-Bildunterschrift für ein Rezept.

        Struktur:
        🍽️ Rezept der Woche: {recipe_name} 🥗

        Zutaten:
        Gib die Zutaten **als echte Liste mit Zeilenumbrüchen** aus – **jede Zutat soll auf einer eigenen Zeile stehen**, mit einem passenden Emoji am Ende der Zeile (z. B. 🥕, 🧅, 🧄, 🧈, 🍋, 🥚 usw.). Verwende **keine HTML-Tags** wie <b> oder <a>.

        Wenn die Zutatenliste länger als 10 Einträge ist, gib **nur die ersten 10 Zutaten** aus, gefolgt von einer Zeile mit „...“.

        Hier ist der Zutatenrohtext:
        {ingredients_text}

        Beende die Caption mit diesem klaren Call-to-Action:

        👉 Die vollständige Zutatenliste und das komplette Rezept finden Sie auf unserer Website:  
        🌐 www.hagengrote.de ➡️ Code: {recipe_id}

        Füge am Ende passende deutschsprachige Hashtags hinzu, z. B.:

        #rezeptderwoche #kochenmitliebe #hausgemacht #schnelleküche #genussmomente #hagengrote #familienrezepte #saisonalkochen #kochenmachtglücklich #rezeptideen
        """

def call_ollama(prompt, model="mistral:latest"):
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0},
    )
    return response["message"]["content"]

def clean_caption(raw_output):
    return re.sub(r"<think>.*?</think>", "", raw_output, flags=re.DOTALL).strip()

def wait_until_ready(media_id):
    for _ in range(10):
        status_res = requests.get(
            f"https://graph.facebook.com/v22.0/{media_id}?fields=status_code",
            params={"access_token": ACCESS_TOKEN},
        )
        status = status_res.json().get("status_code")
        if status == "FINISHED":
            return True
        time.sleep(2)
    return False

def upload_and_publish(image_url, caption):
    res = requests.post(
        f"https://graph.facebook.com/v22.0/{IG_USER_ID}/media",
        params={
            "image_url": image_url,
            "caption": caption,
            "access_token": ACCESS_TOKEN,
        },
    )
    creation_id = res.json().get("id")
    if not creation_id:
        raise Exception(f"Media creation failed: {res.text}")
    if not wait_until_ready(creation_id):
        raise Exception(f"Media {creation_id} not ready in time.")
    pub = requests.post(
        f"https://graph.facebook.com/v22.0/{IG_USER_ID}/media_publish",
        params={"creation_id": creation_id, "access_token": ACCESS_TOKEN},
    )
    return pub.json()

def log_posted_recipe(rezept_id):
    df = pd.DataFrame([[rezept_id, datetime.now()]], columns=["rezept_id", "timestamp"])
    if os.path.exists(LOG_PATH):
        df.to_csv(LOG_PATH, mode="a", header=False, index=False)
    else:
        df.to_csv(LOG_PATH, index=False)

# ========== Main Flow ==========

@flow
def post_recipe_flow():
    # Step 1: Load and filter recipes
    is_text = pd.read_csv("/Volumes/MARAL/CSV/F01/V4AR1005.csv", sep=";", encoding="cp850")
    mar = pd.read_csv("/Volumes/MARAL/CSV/F01/V2AR1001.csv", sep=";", encoding="cp850")

    marketing_istext_merged = mar[["NUMMER", "TEXT_KZ"]].merge(
        is_text, left_on="TEXT_KZ", right_on="TEXTNR", how="outer"
    )
    recipe_data = marketing_istext_merged[marketing_istext_merged["NUMMER"].str.startswith("R", na=False)][
        ["NUMMER", "TEXT_KZ", "STICHWORT", "INTERNET", "KATALOG", "BANAME", "SYS_ANLAGE", "SYS_BEWEG", "TEXT11"]
    ]
    recipe_data = recipe_data[recipe_data["INTERNET"].notna()]
    recipe_data = recipe_data[~recipe_data["STICHWORT"].str.contains(r"^fr", case=False, na=False, regex=True)]

    # Step 2: Check already posted
    try:
        posted_log = pd.read_csv(LOG_PATH)
        posted_ids = posted_log["rezept_id"].astype(str).tolist()
    except FileNotFoundError:
        posted_ids = []

    next_id = next((rid for rid in REZEPT_IDS if rid not in posted_ids), None)
    if not next_id:
        print("✅ All recipes have already been posted.")
        return

    # Step 3: Extract recipe data
    selected_recipe = recipe_data[recipe_data["NUMMER"] == f"R{next_id}"]
    if selected_recipe.empty:
        print(f"❌ Recipe R{next_id} not found in data.")
        return

    recipe_description = selected_recipe.iloc[0]["INTERNET"]
    recipe_name = selected_recipe.iloc[0]["BANAME"]
    recipe_id = selected_recipe.iloc[0]["NUMMER"]

    ingredients_text = clean_ingredients_from_html(recipe_description)
    prompt = create_prompt(recipe_name, ingredients_text, recipe_id)
    response = call_ollama(prompt)
    generated_caption = clean_caption(response)

    r_name = "-".join(recipe_name.split())
    r_full = r_name + "-_-" + recipe_id
    photo_url = f"https://www.hagengrote.de/$WS/hg1ht/websale8_shop-hg1ht/produkte/medien/bilder/gross/{r_full}.jpg"
    photo_url = normalize_german_url(photo_url)

    # Step 4: Upload
    print(f"📸 Posting Recipe: {recipe_id}")
    print(f"📝 Caption:\n{generated_caption}\n")
    print(f"🌐 Image URL: {photo_url}")
    # upload_and_publish(photo_url, generated_caption)

    # Step 5: Log result
    log_posted_recipe(next_id)

# To test manually: python post_recipe_flow.py
if __name__ == "__main__":
    post_recipe_flow()
