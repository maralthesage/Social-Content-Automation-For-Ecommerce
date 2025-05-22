import subprocess
import re
import json

encoding="utf-8"

with open("config/secrets.json", "r", encoding="utf-8") as f:
    secrets = json.load(f)
    
def clean_caption(raw_output):
    # Remove <think>...</think> and surrounding whitespace
    return re.sub(r'<think>.*?</think>', '', raw_output, flags=re.DOTALL).strip()

def generate_caption(description: str, product_name: str, product_id: str, lang: str = "de") -> str:
    prompt = secrets['prompt']

    result = subprocess.run(
        ["ollama", "run", "qwen3:latest"],
        input=prompt.encode(encoding),
        capture_output=True
    )

    if result.returncode != 0:
        raise RuntimeError("Ollama call failed: " + result.stderr.decode(encoding))
    raw_caption = result.stdout.decode(encoding).strip()
    caption = clean_caption(raw_caption)

    return caption

if __name__ == "__main__":
    import csv
    with open("../data/product_list.csv", "r", encoding=encoding) as f:
        products = list(csv.DictReader(f))

    first = products[0]
    caption = generate_caption(first["description"], first["titel"], first["id"])

    with open("../captions/generated_caption.txt", "w", encoding=encoding) as out:
        out.write(caption)

    print("Caption written to file.")