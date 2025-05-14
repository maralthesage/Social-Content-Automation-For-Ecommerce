import subprocess
import re

encoding="utf-8"

def clean_caption(raw_output):
    # Remove <think>...</think> and surrounding whitespace
    return re.sub(r'<think>.*?</think>', '', raw_output, flags=re.DOTALL).strip()


def generate_caption(description: str, product_name: str, lang: str = "de") -> str:
    prompt = f"""
Sie sind ein erfahrener Social-Media-Texter für eine exklusive Premium-Marke im Bereich Genuss, Küche und Kulinarik.

Verfassen Sie einen hochwertigen Instagram-Post auf Deutsch, der das folgende Produkt elegant, inspirierend und markenkonform präsentiert:

• Produktname: {product_name}  
• Produktbeschreibung: {description}

### Anforderungen an Stil und Tonalität:
- Verwenden Sie die **Sie-Form** (formell, kultiviert und vertrauenswürdig)
- Keine umgangssprachlichen oder lockeren Formulierungen
- **Einige dekorativen oder verspielten Emojis** -  ** auch dezente Strukturzeichen wie •, ➤, ✦ oder ✔️ sind erlaubt**, wenn sie zur besseren Gliederung beitragen
- Kurze, elegante Absätze (1-2 Sätze), die klar und emotional ansprechend formuliert sind
- Heben Sie die wichtigsten Vorteile (USPs) in einem natürlichen, fließenden Sprachstil hervor
- Beginnen Sie mit einem wirkungsvollen, einleitenden Satz, der die Aufmerksamkeit weckt
- Integrieren Sie eine stilvolle Handlungsaufforderung (z. B. „Jetzt exklusiv entdecken“)
- Verwenden Sie am Ende 3-5 hochwertige Hashtags, die zur Markenwelt passen (keine generischen Massen-Hashtags)
- Maximale Länge: 2.200 Zeichen

### Wichtig:
Antworten Sie **ausschließlich mit dem fertigen Instagram-Text** - ohne Kommentare, Formatierungen, Erklärungen oder <think>-Elemente.

"""



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
    caption = generate_caption(first["description"], first["titel"])
    

    with open("../captions/generated_caption.txt", "w", encoding=encoding) as out:
        out.write(caption)

    print("Caption written to file.")
