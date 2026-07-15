import re


MEDICINE_REQUEST_PHRASES = [
    "which medicine",
    "best medicine",
    "better medicine",
    "what medicine",
    "suggest medicine",
    "suggest any medicine",
    "medicine for",
    "tablet for",
    "syrup for",
    "can i take",
    "should i take",
    "can i consume",
]


GENERAL_HEALTH_WORDS = [
    "pain",
    "ache",
    "fever",
    "cough",
    "cold",
    "headache",
    "dizziness",
    "dizzy",
    "vomiting",
    "nausea",
    "stomach",
    "throat",
    "chest",
    "breathing",
    "sleep",
    "glucose",
    "bp",
    "blood pressure",
    "diabetes",
    "bmi",
    "prescription",
    "report",
    "medicine",
    "tablet",
    "syrup",
]


SYMPTOM_ALIASES = {
    "headache": ["headache", "head pain", "migraine"],
    "cough": ["cough", "dry cough", "wet cough", "chesty cough"],
    "fever": ["fever", "high temperature", "temperature"],
    "dizziness": ["dizziness", "dizzy", "vertigo", "spinning", "lightheaded", "giddiness"],
    "stomach pain": ["stomach pain", "abdominal pain", "belly pain"],
    "vomiting": ["vomiting", "vomit", "throwing up"],
    "cold": ["cold", "runny nose", "blocked nose", "sneezing"],
    "throat pain": ["throat pain", "sore throat", "throat irritation"],
}


RED_FLAG_WORDS = [
    "chest pain",
    "difficulty breathing",
    "shortness of breath",
    "fainting",
    "passed out",
    "severe headache",
    "worst headache",
    "blood",
    "confusion",
    "weakness",
    "numbness",
    "slurred speech",
    "vision loss",
    "double vision",
    "severe vomiting",
    "unconscious",
]


def normalize_text(text):
    text = text or ""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def is_health_related(query):
    text = normalize_text(query)
    return any(word in text for word in GENERAL_HEALTH_WORDS)


def detect_intent(query):
    text = normalize_text(query)

    if any(phrase in text for phrase in MEDICINE_REQUEST_PHRASES):
        return "medicine_suggestion"

    if "side effect" in text or "side effects" in text:
        return "medicine_side_effect"

    if "dosage" in text or "dose" in text:
        return "dosage_question"

    if "report" in text or "blood test" in text:
        return "report_question"

    if "prescription" in text:
        return "prescription_question"

    return "general_health"


def extract_symptoms(query):
    text = normalize_text(query)
    detected = []

    for symptom, aliases in SYMPTOM_ALIASES.items():
        for alias in aliases:
            if alias in text:
                detected.append(symptom)
                break

    return detected


def has_red_flags(query):
    text = normalize_text(query)
    return any(flag in text for flag in RED_FLAG_WORDS)