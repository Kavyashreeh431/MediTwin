import json
import re
import requests


OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"


def clean_json_text(text):
    if not text:
        return ""

    text = text.strip()
    text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^```", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return match.group(0)

    return text


def extract_prescription_items_with_llm(prescription_text):
    """
    Local Ollama LLM extractor.
    If Ollama is not installed/running, this returns [] safely.
    """

    if not prescription_text or not prescription_text.strip():
        return []

    prompt = f"""
You are a prescription text extraction assistant.

Extract all medicines from the prescription text.

Return ONLY valid JSON array.
Do not add explanation.
Do not add markdown.

Each object must contain:
- medicine_name
- dosage
- frequency
- duration

Rules:
- Do not invent medicine names.
- Extract only medicines clearly present in the text.
- If dosage is missing, use "Not clearly mentioned".
- If frequency is missing, use "Not clearly mentioned".
- If duration is missing, use "Not clearly mentioned".

Prescription text:
{prescription_text}

Return format:
[
  {{
    "medicine_name": "Crocin",
    "dosage": "500mg",
    "frequency": "twice daily",
    "duration": "3 days"
  }}
]
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1
                }
            },
            timeout=45
        )

        if response.status_code != 200:
            print("LLM API error:", response.status_code, response.text[:300])
            return []

        data = response.json()
        raw_output = data.get("response", "")

        print("-------- LLM RAW OUTPUT START --------")
        print(raw_output)
        print("--------- LLM RAW OUTPUT END ---------")

        json_text = clean_json_text(raw_output)
        items = json.loads(json_text)

        if not isinstance(items, list):
            return []

        cleaned_items = []

        for item in items:
            if not isinstance(item, dict):
                continue

            medicine_name = str(item.get("medicine_name", "")).strip()

            if not medicine_name:
                continue

            cleaned_items.append({
                "medicine_name": medicine_name,
                "dosage": str(item.get("dosage", "Not clearly mentioned")).strip(),
                "frequency": str(item.get("frequency", "Not clearly mentioned")).strip(),
                "duration": str(item.get("duration", "Not clearly mentioned")).strip(),
            })

        print("LLM extracted medicines:", cleaned_items)
        return cleaned_items

    except Exception as e:
        print("LLM extraction error:", e)
        return []