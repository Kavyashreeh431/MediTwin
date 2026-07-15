import csv
import re
import requests
from pathlib import Path
from functools import lru_cache
import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

try:
    from .external_medical_api import get_external_medical_context
except Exception:
    def get_external_medical_context(query):
        return "External medical API context is not available."

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-3.5-flash"

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DATASET_PATHS = [
    PROJECT_ROOT / "apps" / "prescription" / "dataset" / "medicine_database.csv",
]

SAFETY_LINE = "For severe or worsening symptoms, please seek in-person medical care."


# =========================================================
# BASIC TEXT HELPERS
# =========================================================

def normalize_text(text):
    if not text:
        return ""

    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def clean_answer(text, add_safety=True):
    if not text:
        return ""

    text = str(text).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)

    remove_phrases = [
        "I am not a doctor,",
        "I'm not a doctor,",
        "I am an AI, not a doctor.",
        "As an AI language model,",
        "As a language model,",
    ]

    for phrase in remove_phrases:
        text = text.replace(phrase, "")

    text = text.strip()

    if add_safety and SAFETY_LINE not in text:
        text = f"{text}\n\n{SAFETY_LINE}"

    return text.strip()


def format_response(opening, points=None, safety=True):
    response_parts = []

    if opening:
        response_parts.append(opening.strip())

    if points:
        if isinstance(points, list):
            response_parts.extend([f"• {point.strip()}" for point in points])
        else:
            response_parts.append(str(points).strip())

    response = "\n".join(response_parts)

    if safety and SAFETY_LINE not in response:
        response = f"{response}\n\n{SAFETY_LINE}"

    return response.strip()


# =========================================================
# GREETING
# =========================================================

def is_greeting_query(query):
    text = normalize_text(query)

    greetings = [
        "hi",
        "hello",
        "hey",
        "hii",
        "hiii",
        "good morning",
        "good afternoon",
        "good evening",
        "namaste",
        "hai",
    ]

    return text in greetings


def greeting_response():
    return (
        "Hi, I’m MediTwin Assistant 😊 How can I help you today? "
        "You can ask me about symptoms, medicines, reports, prescriptions, BMI, sleep, glucose, or general wellness."
    )


# =========================================================
# HEALTHCARE SCOPE CHECKING
# =========================================================

HEALTHCARE_KEYWORDS = [
    "health", "medical", "medicine", "tablet", "capsule", "syrup",
    "drug", "dose", "dosage", "side effect", "side effects",
    "fever", "cold", "cough", "headache", "pain", "ache", "symptom",
    "blood", "glucose", "sugar", "pressure", "bp", "heart",
    "bmi", "weight", "sleep", "exercise", "diet", "report",
    "prescription", "doctor", "hospital", "clinic", "allergy",
    "infection", "vomiting", "vomit", "diarrhea", "dizziness",
    "dizzy", "vertigo", "fatigue", "cholesterol", "hemoglobin",
    "wbc", "rbc", "platelet", "thyroid", "diabetes", "stomach",
    "abdominal", "belly", "dairy", "acidity", "digestion", "injury",
    "rash", "asthma", "breathing", "nausea", "body ache", "weakness",
    "lactose", "gas", "heartburn", "throat", "sore throat",
    "migraine", "dehydration", "constipation", "urine", "period",
    "cramps", "skin", "swelling", "burning", "itching", "ear",
    "eye", "nose", "sinus", "infection",
]

NON_HEALTH_KEYWORDS = [
    "python", "django", "java", "html", "css", "javascript",
    "code", "program", "recipe", "cook", "politics", "election",
    "movie", "song", "game", "travel", "business plan", "resume",
]


def is_health_related(query):
    text = normalize_text(query)
    return any(word in text for word in HEALTHCARE_KEYWORDS)


def is_non_healthcare_query(query):
    text = normalize_text(query)

    has_health_word = any(word in text for word in HEALTHCARE_KEYWORDS)
    has_non_health_word = any(word in text for word in NON_HEALTH_KEYWORDS)

    return has_non_health_word and not has_health_word


def scope_boundary_response():
    return (
        "I’m here to help with health-related questions only. "
        "You can ask about symptoms, medicines, reports, prescriptions, BMI, sleep, glucose, or general wellness."
    )


# =========================================================
# GENERIC INTENT + SYMPTOM ENGINE
# =========================================================

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
    "capsule for",
    "can i take",
    "can i consume",
    "can i use",
    "should i take",
    "is it safe",
    "is it okay",
]

MEDICINE_SAFETY_PHRASES = [
    "safe",
    "with",
    "combine",
    "together",
    "interaction",
    "can i take it with",
    "can i combine",
]

MEDICINE_INFO_PHRASES = [
    "use",
    "used for",
    "purpose",
    "what is",
    "why is",
]

DOSAGE_PHRASES = [
    "dosage",
    "dose",
    "how many",
    "how much",
    "frequency",
    "times a day",
]

SIDE_EFFECT_PHRASES = [
    "side effect",
    "side effects",
    "reaction",
    "allergic reaction",
]


SYMPTOM_KNOWLEDGE = {
    "headache": {
        "aliases": ["headache", "head pain", "migraine"],
        "followup": "Is the headache mild, severe, sudden, or repeated?",
    },
    "cough": {
        "aliases": ["cough", "dry cough", "wet cough", "chesty cough"],
        "followup": "Is your cough dry or with mucus?",
    },
    "fever": {
        "aliases": ["fever", "high temperature", "temperature"],
        "followup": "How high is the fever and how many days has it been there?",
    },
    "dizziness": {
        "aliases": ["dizziness", "dizzy", "vertigo", "spinning", "lightheaded", "giddiness"],
        "followup": "Do you feel spinning, faintness, or imbalance?",
    },
    "stomach pain": {
        "aliases": ["stomach pain", "abdominal pain", "belly pain", "stomach ache"],
        "followup": "Where exactly is the pain and when did it start?",
    },
    "vomiting": {
        "aliases": ["vomiting", "vomit", "throwing up", "nausea"],
        "followup": "How many times have you vomited today?",
    },
    "cold": {
        "aliases": ["cold", "runny nose", "blocked nose", "sneezing"],
        "followup": "Do you also have fever, cough, throat pain, or breathing difficulty?",
    },
    "throat pain": {
        "aliases": ["throat pain", "sore throat", "throat irritation"],
        "followup": "Do you have fever, cough, or difficulty swallowing?",
    },
    "acidity": {
        "aliases": ["acidity", "heartburn", "gas", "acid reflux", "burning stomach"],
        "followup": "Does it happen after meals or while lying down?",
    },
    "diarrhea": {
        "aliases": ["diarrhea", "loose motion", "loose motions"],
        "followup": "How many times did it happen today and do you have fever or blood in stool?",
    },
    "body pain": {
        "aliases": ["body pain", "body ache", "muscle pain", "joint pain"],
        "followup": "Is the pain after exercise, fever, injury, or without any clear reason?",
    },
    "rash": {
        "aliases": ["rash", "skin rash", "itching", "red spots"],
        "followup": "Is there itching, swelling, fever, or allergy history?",
    },
}


RED_FLAG_WORDS = [
    "severe chest pain",
    "chest pain",
    "breathing difficulty",
    "difficulty breathing",
    "severe shortness of breath",
    "shortness of breath",
    "sudden numbness",
    "numbness one side",
    "face drooping",
    "slurred speech",
    "severe bleeding",
    "heavy bleeding",
    "unconscious",
    "stroke",
    "heart attack",
    "seizure",
    "poison",
    "severe allergic reaction",
    "swelling of face",
    "blue lips",
    "very high fever",
    "fainted",
    "fainting",
    "passed out",
    "blood vomiting",
    "black stool",
    "suicidal",
    "suicide",
    "self harm",
    "worst headache",
    "severe headache",
    "vision loss",
    "double vision",
    "confusion",
    "cannot walk",
    "continuous vomiting",
    "blood in cough",
    "blood in stool",
]


def detect_intent(query):
    text = normalize_text(query)

    if is_greeting_query(query):
        return "greeting"

    if emergency_response(query):
        return "emergency"

    if any(phrase in text for phrase in SIDE_EFFECT_PHRASES):
        return "medicine_side_effect"

    if any(phrase in text for phrase in DOSAGE_PHRASES):
        return "dosage_question"

    if any(phrase in text for phrase in MEDICINE_SAFETY_PHRASES):
        return "medicine_safety"

    if any(phrase in text for phrase in MEDICINE_REQUEST_PHRASES):
        return "medicine_suggestion"

    if any(phrase in text for phrase in MEDICINE_INFO_PHRASES):
        return "medicine_info"

    if "report" in text or "blood test" in text or "hemoglobin" in text:
        return "report_help"

    if "prescription" in text:
        return "prescription_help"

    if extract_symptoms(query):
        return "symptom_question"

    return "general_health"


def extract_symptoms(query):
    text = normalize_text(query)
    detected = []

    for symptom, info in SYMPTOM_KNOWLEDGE.items():
        aliases = info.get("aliases", [])

        for alias in aliases:
            if alias in text:
                detected.append(symptom)
                break

    if not detected and "pain" in text:
        detected.append("pain")

    if not detected and "ache" in text:
        detected.append("pain")

    return detected


def get_symptom_followup(symptoms):
    if not symptoms:
        return "Please tell me more about the symptom, how long it has been happening, and how severe it is."

    followups = []

    for symptom in symptoms:
        info = SYMPTOM_KNOWLEDGE.get(symptom)
        if info and info.get("followup"):
            followups.append(info["followup"])

    if followups:
        return " ".join(followups)

    return "Please tell me when it started, how severe it is, and whether it is getting worse."


def has_red_flags(query):
    text = normalize_text(query)
    return any(flag in text for flag in RED_FLAG_WORDS)


def emergency_response(query):
    if has_red_flags(query):
        return (
            "That sounds potentially serious. Please seek urgent medical help immediately "
            "or call your local emergency number now. Do not wait for an online response."
        )

    return None


# =========================================================
# MEDICINE DATASET
# =========================================================

def get_medicine_csv_path():
    for path in DATASET_PATHS:
        if path.exists():
            return path
    return DATASET_PATHS[0]


@lru_cache(maxsize=1)
def load_medicine_database():
    medicines = {}
    medicine_csv_path = get_medicine_csv_path()

    if not medicine_csv_path.exists():
        print("Assistant medicine CSV not found:", medicine_csv_path)
        return medicines

    try:
        with open(medicine_csv_path, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                key = normalize_text(row.get("key", ""))

                if not key:
                    continue

                aliases = row.get("aliases", "")
                alias_list = []

                if aliases:
                    alias_list = [
                        normalize_text(alias)
                        for alias in re.split(r"[|,;/]+", aliases)
                        if normalize_text(alias)
                    ]

                medicines[key] = {
                    "key": key,
                    "display_name": row.get("display_name", key).strip(),
                    "aliases": alias_list,
                    "ingredients": row.get("ingredients", "Not available").strip(),
                    "purpose": row.get("purpose", "Not available").strip(),
                    "common_dosage": row.get("common_dosage", "Use only as prescribed.").strip(),
                    "common_frequency": row.get("common_frequency", "Follow doctor's prescription.").strip(),
                    "side_effects": row.get("side_effects", "Not available").strip(),
                    "warnings": row.get("warnings", "Consult doctor/pharmacist before use.").strip(),
                    "avoid_if": row.get("avoid_if", "Avoid if allergic to this medicine.").strip(),
                }

        print("Assistant loaded medicine dataset:", len(medicines))

    except Exception as e:
        print("Assistant medicine dataset loading error:", e)

    return medicines


def find_relevant_medicines(query, limit=3):
    medicines = load_medicine_database()
    normalized_query = normalize_text(query)

    matched = []

    for key, data in medicines.items():
        search_terms = [
            key,
            normalize_text(data.get("display_name", "")),
            normalize_text(data.get("ingredients", "")),
        ]

        search_terms.extend(data.get("aliases", []))

        for term in search_terms:
            if not term:
                continue

            pattern = r"\b" + re.escape(term) + r"\b"

            if re.search(pattern, normalized_query):
                matched.append(data)
                break

    return matched[:limit]


def build_medicine_context(medicines):
    if not medicines:
        return "No medicine from the local dataset was directly matched."

    context_parts = []

    for med in medicines:
        context_parts.append(
            f"""
Medicine: {med['display_name']}
Ingredients: {med['ingredients']}
Purpose: {med['purpose']}
Common Dosage: {med['common_dosage']}
Common Frequency: {med['common_frequency']}
Side Effects: {med['side_effects']}
Warnings: {med['warnings']}
Avoid If: {med['avoid_if']}
""".strip()
        )

    return "\n\n".join(context_parts)


# =========================================================
# GENERIC SAFE RESPONSE ENGINE
# =========================================================

def generate_generic_medicine_guidance(query, symptoms, medicines, intent):
    symptom_text = ", ".join(symptoms) if symptoms else "your symptom"

    if emergency_response(query):
        return emergency_response(query)

    if medicines:
        med = medicines[0]
        name = med.get("display_name", "this medicine")
        purpose = med.get("purpose", "Not available")
        frequency = med.get("common_frequency", "Follow doctor's prescription.")
        side_effects = med.get("side_effects", "Not available")
        warnings = med.get("warnings", "Consult doctor/pharmacist before use.")
        avoid_if = med.get("avoid_if", "Avoid if allergic to this medicine.")

        if intent == "medicine_side_effect":
            return format_response(
                f"Here is general side-effect information about {name}.",
                [
                    f"Possible side effects: {side_effects}",
                    f"Warnings: {warnings}",
                    f"Avoid if: {avoid_if}",
                    "If you have rash, swelling, breathing difficulty, fainting, or severe reaction, seek urgent medical care."
                ],
                safety=True
            )

        if intent == "dosage_question":
            return format_response(
                f"I cannot safely decide the exact dose of {name} for you.",
                [
                    f"General frequency information from local data: {frequency}",
                    "Dose depends on age, weight, medical condition, pregnancy status, liver/kidney health, and other medicines.",
                    "Please follow the label, prescription, or ask a doctor/pharmacist before taking it."
                ],
                safety=True
            )

        if intent == "medicine_safety":
            return format_response(
                f"Whether {name} is safe for you depends on your health condition and other medicines.",
                [
                    f"Purpose: {purpose}",
                    f"Warnings: {warnings}",
                    f"Avoid if: {avoid_if}",
                    "Tell me what other medicine you want to take it with, and whether you have allergies, liver/kidney problems, pregnancy, or long-term illness.",
                    "For exact safety confirmation, ask a doctor or pharmacist."
                ],
                safety=True
            )

        if symptoms:
            return format_response(
                f"{name} may help only if it is suitable for the cause of {symptom_text}.",
                [
                    f"Local medicine purpose: {purpose}",
                    "Do not take it randomly or in extra doses.",
                    f"Important warning: {warnings}",
                    get_symptom_followup(symptoms),
                    "Confirm use and dosage with a doctor or pharmacist, especially if symptoms are severe, repeated, or worsening."
                ],
                safety=True
            )

        return format_response(
            f"That’s a good question about {name}.",
            [
                f"Purpose: {purpose}",
                f"Common frequency: {frequency}",
                f"Possible side effects: {side_effects}",
                f"Warnings: {warnings}",
                "Please confirm use and dosage with a doctor or pharmacist."
            ],
            safety=True
        )

    if intent == "medicine_suggestion":
        return format_response(
            f"Medicine for {symptom_text} depends on the exact cause, so I should not suggest one medicine directly.",
            [
                "Different causes may need different treatment.",
                "A pharmacist or doctor can suggest the safest medicine based on your age, allergies, existing conditions, and other medicines.",
                get_symptom_followup(symptoms),
                "Avoid taking random tablets without checking the label or asking a pharmacist."
            ],
            safety=True
        )

    return None


def generate_generic_symptom_guidance(query, symptoms):
    if emergency_response(query):
        return emergency_response(query)

    symptom_text = ", ".join(symptoms) if symptoms else "your symptom"

    return format_response(
        f"{symptom_text.capitalize()} can happen for different reasons, so the cause matters.",
        [
            "Drink water and rest if symptoms are mild.",
            "Avoid self-medicating if you are unsure of the cause.",
            get_symptom_followup(symptoms),
            "If symptoms are severe, repeated, unusual, or worsening, consult a doctor."
        ],
        safety=True
    )


def fast_response(query, medicines):
    """
    Fast local answer.
    This avoids Ollama for common and safety-sensitive cases.
    It is generic, not one separate function for every symptom.
    """
    text = normalize_text(query)
    intent = detect_intent(query)
    symptoms = extract_symptoms(query)

    urgent = emergency_response(query)
    if urgent:
        return urgent

    if medicines and intent in [
        "medicine_suggestion",
        "medicine_safety",
        "medicine_info",
        "medicine_side_effect",
        "dosage_question",
    ]:
        response = generate_generic_medicine_guidance(
            query=query,
            symptoms=symptoms,
            medicines=medicines,
            intent=intent,
        )

        if response:
            return response

    if intent == "medicine_suggestion":
        response = generate_generic_medicine_guidance(
            query=query,
            symptoms=symptoms,
            medicines=medicines,
            intent=intent,
        )

        if response:
            return response

    if symptoms:
        return generate_generic_symptom_guidance(query, symptoms)

    if "bmi" in text or "weight" in text:
        return format_response(
            "That’s a useful health question.",
            [
                "BMI is a height-weight estimate, but it does not show complete health.",
                "Focus on balanced food, sleep, exercise, and regular tracking.",
                "Discuss very low or very high BMI with a doctor."
            ],
            safety=True
        )

    if "prescription" in text:
        return format_response(
            "I can help you understand prescription information in a simple way.",
            "Use the Prescription Analyzer module to check medicine name, dosage, frequency, and warnings. Always verify handwritten prescription results with a doctor or pharmacist.",
            safety=True
        )

    if "report" in text or "blood test" in text:
        return format_response(
            "I can help explain report values in simple language.",
            "Use the Report Summarizer module to understand values like glucose, hemoglobin, WBC, RBC, or cholesterol. Abnormal values should be discussed with a doctor.",
            safety=True
        )

    return None


# =========================================================
# CHAT HISTORY CONTEXT
# =========================================================

def build_chat_history_context(chat_history, limit=4):
    if not chat_history:
        return "No previous chat context."

    recent_items = chat_history[-limit:]
    context_lines = []

    for item in recent_items:
        question = str(item.get("question", "")).strip()
        answer = str(item.get("answer", "")).strip()

        if len(answer) > 250:
            answer = answer[:250] + "..."

        context_lines.append(
            f"User: {question}\nAssistant: {answer}"
        )

    return "\n\n".join(context_lines)


def is_contextual_query(query):
    text = normalize_text(query)
    words = text.split()

    contextual_words = [
        "it", "its", "itself",
        "this", "that",
        "they", "them", "those",
        "same", "above", "previous",
        "medicine", "tablet", "capsule", "syrup"
    ]

    contextual_phrases = [
        "what about it",
        "what is it",
        "is it safe",
        "is it okay",
        "can i take it",
        "can i consume it",
        "can i use it",
        "side effects of it",
        "side effects of that",
        "what are its side effects",
        "its side effects",
        "how to use it",
        "what is its use",
        "tell more about it",
        "explain it",
        "for that",
        "about that",
        "same medicine",
        "that medicine",
        "same tablet",
        "that tablet",
        "its dosage",
        "its dose",
        "its warning",
        "its purpose",
        "is that safe",
        "can i take that",
    ]

    if any(phrase in text for phrase in contextual_phrases):
        return True

    if len(words) <= 10 and any(word in words for word in contextual_words):
        return True

    return False


def extract_topic_from_user_question(question):
    """
    Important:
    Extract topic only from the previous USER question.
    Do not use assistant answer here because assistant answer may contain
    extra symptom/safety words and can confuse 'it' or 'that'.
    """
    text = normalize_text(question)

    medicines = find_relevant_medicines(text, limit=1)

    if medicines:
        return medicines[0].get("display_name") or medicines[0].get("key")

    symptoms = extract_symptoms(text)

    if symptoms:
        return symptoms[0]

    possible_topics = [
        "glucose",
        "bmi",
        "weight",
        "blood pressure",
        "sleep",
        "prescription",
        "report",
        "medicine",
        "tablet",
        "capsule",
        "syrup",
    ]

    for topic in possible_topics:
        if topic in text:
            return topic

    return None


def get_last_topic_from_history(chat_history):
    if not chat_history:
        return None

    for item in reversed(chat_history):
        previous_question = str(item.get("question", "")).strip()

        topic = extract_topic_from_user_question(previous_question)

        if topic:
            return topic

    return None


def resolve_contextual_query(query, chat_history):
    if not is_contextual_query(query):
        return query

    last_topic = get_last_topic_from_history(chat_history)

    if not last_topic:
        return query

    return (
        f"{query} "
        f"[Context: In this question, words like 'it', 'its', 'this', or 'that' refer to {last_topic}. "
        f"Answer only about {last_topic}.]"
    )

# =========================================================
# OLLAMA AI RESPONSE
# =========================================================
# - Answer only health-related questions.
def ask_gemini(
    query,
    medicine_context,
    chat_context="No previous chat context.",
    external_context="No external context."
):
    if not GEMINI_API_KEY:
        print("Gemini API key missing.")
        return None

    prompt = f"""
You are MediTwin Assistant, a safe virtual healthcare assistant.

Rules:

- Use recent chat context to understand words like "it", "this", "that", or "same medicine".
- Do not diagnose.
- Do not prescribe medicines.
- Do not invent medicine names, dosage, or treatment.
- For medicine-suggestion questions, explain that the best medicine depends on the cause.
- Ask one useful follow-up question when symptom details are missing.
- For emergency symptoms, advise urgent in-person medical care.
- Keep the answer short, clear, friendly, and practical.
- Do not say "I am an AI" or "I am not a doctor".
- End with this exact safety line when giving health advice:
{SAFETY_LINE}

Recent chat context:
{chat_context}

Local MediTwin medicine context:
{medicine_context}

External trusted medical context:
{external_context}

User question:
{query}

Give a short, helpful, safe answer in simple words:
"""

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

        answer = response.text.strip()

        if not answer:
            return None

        return clean_answer(answer, add_safety=True)

    except Exception as e:
        print("Gemini error:", e)
        return None

# =========================================================
# FALLBACK
# =========================================================

def fallback_response(query, medicines):
    response = fast_response(query, medicines)

    if response:
        return response

    if is_health_related(query):
        return format_response(
            "I can help with this health question, but I need a little more detail.",
            [
                "Please mention the symptom clearly.",
                "Tell me how long it has been happening and how severe it is.",
                "If you are asking about medicine, mention the medicine name if you know it."
            ],
            safety=True
        )

    return (
        "I can help with symptoms, medicines, prescriptions, reports, BMI, glucose, sleep, and general wellness. "
        "Please type your health question in simple words."
    )

def generate_contextual_after_meal_answer(query, chat_history):
    """
    Handles short follow-up replies like:
    - after meal
    - after food
    - after eating
    - fasting
    - before meal

    It answers based on the previous topic.
    It will not always assume glucose.
    """
    text = normalize_text(query)

    meal_timing_phrases = [
        "after meal",
        "after food",
        "after eating",
        "2 hours after meal",
        "two hours after meal",
        "fasting",
        "before meal",
        "before food",
        "before eating",
        "random",
    ]

    if not any(phrase in text for phrase in meal_timing_phrases):
        return None

    last_topic = get_last_topic_from_history(chat_history)

    if not last_topic:
        return format_response(
            "Meal timing can mean different things depending on the health topic.",
            [
                "Please tell me whether you are asking about blood sugar, stomach pain, acidity, medicine timing, or another symptom."
            ],
            safety=True
        )

    topic_text = normalize_text(last_topic)

    # Case 1: Glucose / sugar context
    if "glucose" in topic_text or "sugar" in topic_text:
        if (
            "after meal" in text
            or "after food" in text
            or "after eating" in text
            or "2 hours" in text
            or "two hours" in text
        ):
            return format_response(
                "For adults, after-meal blood glucose is usually checked about 2 hours after starting food.",
                [
                    "For a person without diabetes, less than 140 mg/dL is generally considered normal.",
                    "140 to 199 mg/dL can suggest prediabetes range.",
                    "200 mg/dL or above may suggest diabetes range if confirmed by proper testing.",
                    "If you already have diabetes, your target range may be different."
                ],
                safety=True
            )

        if "fasting" in text or "before meal" in text or "before food" in text or "before eating" in text:
            return format_response(
                "For adults, fasting blood glucose means sugar level before eating, usually after overnight fasting.",
                [
                    "Normal fasting glucose is usually less than 100 mg/dL.",
                    "100 to 125 mg/dL can suggest prediabetes range.",
                    "126 mg/dL or above may suggest diabetes range if confirmed by proper testing."
                ],
                safety=True
            )

        if "random" in text:
            return format_response(
                "Random glucose means blood sugar checked at any time of the day.",
                [
                    "A single random value is harder to understand without meal timing and symptoms.",
                    "Very high random glucose with thirst, frequent urination, or weight loss should be checked by a doctor."
                ],
                safety=True
            )

    # Case 2: Stomach/acidity/digestion context
    if topic_text in ["stomach pain", "stomach", "acidity", "digestion", "heartburn", "gas"]:
        return format_response(
            f"If {last_topic} happens after meals, it may be related to digestion, acidity, food intolerance, or eating habits.",
            [
                "Try noticing whether it happens after spicy, oily, dairy, or heavy food.",
                "Eat smaller meals and avoid lying down immediately after eating.",
                "Seek medical care if pain is severe, repeated, or comes with vomiting, fever, weight loss, black stool, or blood."
            ],
            safety=True
        )

    # Case 3: Medicine/tablet context
    if topic_text in ["medicine", "tablet", "capsule", "syrup"] or find_relevant_medicines(last_topic, limit=1):
        return format_response(
            "Medicine timing before or after food depends on the exact medicine.",
            [
                "Some medicines are taken after food to reduce stomach irritation.",
                "Some medicines must be taken before food for better effect.",
                "Please mention the medicine name so I can explain the general instruction from the dataset."
            ],
            safety=True
        )

    # Case 4: Other symptom context
    symptoms = extract_symptoms(topic_text)

    if symptoms or topic_text in [
        "headache",
        "cough",
        "cold",
        "fever",
        "vomiting",
        "diarrhea",
        "dizziness",
        "rash",
        "body pain",
        "throat pain",
    ]:
        return format_response(
            f"If {last_topic} is happening after meals, the cause depends on the symptom and food pattern.",
            [
                "Please tell me what food you ate and how soon the symptom started after eating.",
                "Also mention whether it is mild, moderate, or severe.",
                "Seek care if it is severe, repeated, or worsening."
            ],
            safety=True
        )

    # Default clarification
    return format_response(
        "I need a little more context to answer correctly.",
        [
            f"Are you asking about {last_topic} after meals, or about blood sugar after meals?",
            "Please mention the exact health topic or value."
        ],
        safety=True
    )
# =========================================================
# MAIN FUNCTION USED BY views.py
# =========================================================

def generate_assistant_response(query, chat_history=None):
    if not query or not query.strip():
        return "Please type a health-related question."

    chat_history = chat_history or []

    # Greeting should be answered directly
    # Greeting should be answered directly
    if is_greeting_query(query):
        return greeting_response()

    # Handles short replies like "after meal" based on previous topic
    contextual_after_meal_answer = generate_contextual_after_meal_answer(
        query,
        chat_history
    )

    if contextual_after_meal_answer:
        return contextual_after_meal_answer

    resolved_query = resolve_contextual_query(query, chat_history)

    if is_non_healthcare_query(resolved_query):
        return scope_boundary_response()

    urgent = emergency_response(resolved_query)

    if urgent:
        return urgent

    medicines = find_relevant_medicines(resolved_query)

    quick_answer = fast_response(resolved_query, medicines)

    if quick_answer:
        return quick_answer

    medicine_context = build_medicine_context(medicines)
    chat_context = build_chat_history_context(chat_history)

    gemini_answer = ask_gemini(
    resolved_query,
    medicine_context,
    chat_context
)

    if gemini_answer:
         return gemini_answer

    return fallback_response(resolved_query, medicines)
    