import requests
import xml.etree.ElementTree as ET
from functools import lru_cache


RXNORM_BASE_URL = "https://rxnav.nlm.nih.gov/REST"
OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"
MEDLINEPLUS_SEARCH_URL = "https://wsearch.nlm.nih.gov/ws/query"


MEDICINE_ALIASES = {
    "paracetamol": "acetaminophen",
    "crocin": "acetaminophen",
    "calpol": "acetaminophen",
}


def normalize_query_text(text):
    return (text or "").strip().lower()


def extract_possible_medicine_name(query):
    """
    Simple beginner-safe medicine extraction.
    Later, this can be replaced with better NLP.
    """
    text = normalize_query_text(query)

    known_medicines = [
        "paracetamol",
        "acetaminophen",
        "ibuprofen",
        "cetirizine",
        "amoxicillin",
        "azithromycin",
        "aspirin",
        "crocin",
        "calpol",
    ]

    for medicine in known_medicines:
        if medicine in text:
            return MEDICINE_ALIASES.get(medicine, medicine)

    return None


@lru_cache(maxsize=128)
def get_rxnorm_name(medicine_name):
    """
    Uses RxNorm to normalize a medicine name.
    Example: paracetamol can be mapped manually to acetaminophen first.
    """
    if not medicine_name:
        return None

    medicine_name = MEDICINE_ALIASES.get(
        medicine_name.lower(),
        medicine_name.lower()
    )

    try:
        response = requests.get(
            f"{RXNORM_BASE_URL}/rxcui.json",
            params={"name": medicine_name},
            timeout=8,
        )

        if response.status_code != 200:
            return medicine_name

        data = response.json()
        rxnorm_id = data.get("idGroup", {}).get("rxnormId", [])

        if not rxnorm_id:
            return medicine_name

        return medicine_name

    except Exception:
        return medicine_name


@lru_cache(maxsize=128)
def get_openfda_drug_label(medicine_name):
    """
    Fetches medicine label information from openFDA.
    Works better with generic US names like acetaminophen instead of paracetamol.
    """
    if not medicine_name:
        return None

    medicine_name = MEDICINE_ALIASES.get(
        medicine_name.lower(),
        medicine_name.lower()
    )

    search_queries = [
        f'openfda.generic_name:"{medicine_name}"',
        f'openfda.substance_name:"{medicine_name}"',
        f'openfda.brand_name:"{medicine_name}"',
    ]

    for search_query in search_queries:
        try:
            response = requests.get(
                OPENFDA_LABEL_URL,
                params={
                    "search": search_query,
                    "limit": 1,
                },
                timeout=10,
            )

            if response.status_code != 200:
                continue

            data = response.json()
            results = data.get("results", [])

            if not results:
                continue

            item = results[0]

            return {
                "source": "openFDA Drug Label API",
                "medicine": medicine_name,
                "purpose": first_value(item.get("purpose")),
                "indications": first_value(item.get("indications_and_usage")),
                "warnings": first_value(item.get("warnings")),
                "do_not_use": first_value(item.get("do_not_use")),
                "ask_doctor": first_value(item.get("ask_doctor")),
                "side_effects": first_value(item.get("adverse_reactions")),
            }

        except Exception:
            continue

    return None


@lru_cache(maxsize=128)
def get_medlineplus_topic(query):
    """
    Fetches patient-friendly topic information from MedlinePlus.
    Useful for cough, fever, headache, cold, diabetes, etc.
    """
    if not query:
        return None

    try:
        response = requests.get(
            MEDLINEPLUS_SEARCH_URL,
            params={
                "db": "healthTopics",
                "term": query,
            },
            timeout=10,
        )

        if response.status_code != 200:
            return None

        root = ET.fromstring(response.text)

        document = root.find(".//document")
        if document is None:
            return None

        title = ""
        snippet = ""
        url = ""

        for content in document.findall("content"):
            name = content.attrib.get("name")

            if name == "title":
                title = content.text or ""

            elif name == "FullSummary":
                snippet = content.text or ""

            elif name == "url":
                url = content.text or ""

        return {
            "source": "MedlinePlus",
            "title": clean_xml_text(title),
            "summary": clean_xml_text(snippet),
            "url": url,
        }

    except Exception:
        return None


def first_value(value):
    if isinstance(value, list) and value:
        return value[0]
    if isinstance(value, str):
        return value
    return ""


def clean_xml_text(text):
    if not text:
        return ""

    return (
        text.replace("<p>", "")
        .replace("</p>", "")
        .replace("<ul>", "")
        .replace("</ul>", "")
        .replace("<li>", "• ")
        .replace("</li>", "\n")
        .strip()
    )


def get_external_medical_context(query):
    """
    Main function used by assistant_engine.py.
    Returns external medical context as plain text.
    """
    medicine_name = extract_possible_medicine_name(query)

    context_parts = []

    if medicine_name:
        normalized_name = get_rxnorm_name(medicine_name)
        drug_label = get_openfda_drug_label(normalized_name)

        if drug_label:
            context_parts.append(
                f"""
External medicine source: {drug_label["source"]}
Medicine: {drug_label["medicine"]}
Purpose: {drug_label["purpose"]}
Indications/Usage: {drug_label["indications"]}
Warnings: {drug_label["warnings"]}
Do not use: {drug_label["do_not_use"]}
Ask doctor: {drug_label["ask_doctor"]}
Side effects: {drug_label["side_effects"]}
""".strip()
            )

    medline_topic = get_medlineplus_topic(query)

    if medline_topic:
        context_parts.append(
            f"""
External health source: {medline_topic["source"]}
Topic: {medline_topic["title"]}
Summary: {medline_topic["summary"]}
""".strip()
        )

    if not context_parts:
        return "No external medical API context found."

    return "\n\n".join(context_parts)