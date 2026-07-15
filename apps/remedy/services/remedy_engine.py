import re


SAFETY_LINE = "For severe or worsening symptoms, please seek in-person medical care."


# -------------------------------------------------
# BASIC TEXT HELPERS
# -------------------------------------------------

def normalize_text(text):
    if not text:
        return ""

    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def contains_any(text, keywords):
    for keyword in keywords:
        keyword = normalize_text(keyword)

        if keyword and keyword in text:
            return True

    return False


def format_confidence(score, total):
    if total <= 0:
        return 0

    confidence = round((score / total) * 100, 2)

    if confidence > 95:
        confidence = 95

    return confidence


# -------------------------------------------------
# EMERGENCY / RED FLAG CHECK
# -------------------------------------------------

EMERGENCY_KEYWORDS = [
    "chest pain",
    "chest tightness",
    "difficulty breathing",
    "shortness of breath",
    "breathing problem",
    "cannot breathe",
    "severe breathing",
    "stroke",
    "seizure",
    "unconscious",
    "fainting",
    "blue lips",
    "confusion",
    "blood vomiting",
    "vomiting blood",
    "blood in stool",
    "black stool",
    "severe dehydration",
    "very high fever",
    "fever 105",
    "fever 104",
    "severe abdominal pain",
    "severe stomach pain",
    "severe headache",
    "stiff neck",
]


def check_emergency(symptom_text):
    text = normalize_text(symptom_text)

    matched_red_flags = []

    for keyword in EMERGENCY_KEYWORDS:
        if keyword in text:
            matched_red_flags.append(keyword)

    if matched_red_flags:
        return {
            "is_emergency": True,
            "matched_red_flags": matched_red_flags,
            "predicted_disease": "Possible emergency warning signs",
            "confidence": 95,
            "severity": "High",
            "remedies": [
                "Do not rely on home remedies for these symptoms.",
                "Seek urgent in-person medical care immediately.",
                "If breathing difficulty, chest pain, fainting, seizure, or severe weakness is present, contact emergency medical services."
            ],
            "advice": [
                "Avoid delaying treatment.",
                "Keep the patient seated or lying safely.",
                "Do not give unknown medicines without medical advice.",
                SAFETY_LINE
            ]
        }

    return {
        "is_emergency": False,
        "matched_red_flags": []
    }


# -------------------------------------------------
# SYMPTOM GROUPS
# -------------------------------------------------

SYMPTOM_SYNONYMS = {
    "fever": [
        "fever",
        "temperature",
        "high temperature",
        "hot body",
        "body heat"
    ],
    "cough": [
        "cough",
        "coughing"
    ],
    "cold": [
        "cold",
        "runny nose",
        "sneezing",
        "blocked nose",
        "stuffy nose",
        "nasal congestion"
    ],
    "throat_pain": [
        "throat pain",
        "sore throat",
        "throat irritation",
        "pain in throat"
    ],
    "headache": [
        "headache",
        "head pain",
        "migraine"
    ],
    "body_pain": [
        "body pain",
        "body ache",
        "muscle pain",
        "muscle ache",
        "joint pain"
    ],
    "stomach_pain": [
        "stomach pain",
        "abdominal pain",
        "belly pain",
        "stomach ache",
        "abdominal cramps",
        "cramps"
    ],
    "acidity": [
        "acidity",
        "acid reflux",
        "heartburn",
        "gas",
        "indigestion",
        "burning stomach",
        "burning sensation"
    ],
    "vomiting": [
        "vomiting",
        "vomit",
        "nausea",
        "feeling vomiting"
    ],
    "diarrhea": [
        "diarrhea",
        "loose motion",
        "loose motions",
        "watery stool",
        "frequent stool"
    ],
    "allergy": [
        "allergy",
        "itching",
        "rash",
        "skin rash",
        "hives",
        "red spots",
        "watery eyes"
    ],
    "dizziness": [
        "dizziness",
        "dizzy",
        "giddiness",
        "light headed",
        "lightheaded"
    ],
    "fatigue": [
        "fatigue",
        "tiredness",
        "weakness",
        "low energy"
    ]
}


def extract_symptom_labels(symptom_text):
    text = normalize_text(symptom_text)

    detected = []

    for label, keywords in SYMPTOM_SYNONYMS.items():
        if contains_any(text, keywords):
            detected.append(label)

    return detected


# -------------------------------------------------
# CONDITION KNOWLEDGE BASE
# -------------------------------------------------

CONDITIONS = [
    {
        "name": "Common Cold / Upper Respiratory Infection",
        "symptoms": ["cold", "cough", "throat_pain", "fever", "headache"],
        "strong_symptoms": ["cold", "cough", "throat_pain"],
        "severity": "Low to Moderate",
        "remedies": [
            "Drink warm fluids and stay hydrated.",
            "Take steam inhalation for nasal blockage if comfortable.",
            "Do warm salt-water gargling for throat irritation.",
            "Take adequate rest.",
            "Avoid cold drinks, dust, smoke, and strong smells."
        ],
        "advice": [
            "If fever is high, cough is worsening, or symptoms last many days, consult a doctor.",
            "If breathing difficulty or chest pain occurs, seek urgent medical care.",
            SAFETY_LINE
        ]
    },
    {
        "name": "Fever / Viral Illness",
        "symptoms": ["fever", "body_pain", "headache", "fatigue", "cold", "cough"],
        "strong_symptoms": ["fever"],
        "severity": "Moderate",
        "remedies": [
            "Drink enough water and fluids.",
            "Take proper rest.",
            "Use a light blanket and avoid overheating.",
            "Eat simple, light food if appetite is low.",
            "Monitor temperature regularly."
        ],
        "advice": [
            "Consult a doctor if fever is very high, lasts more than 2 days, or comes with rash, severe weakness, breathing difficulty, confusion, or dehydration.",
            "Do not self-use antibiotics for fever.",
            SAFETY_LINE
        ]
    },
    {
        "name": "Dry Cough / Throat Irritation",
        "symptoms": ["cough", "throat_pain", "cold"],
        "strong_symptoms": ["cough"],
        "severity": "Low to Moderate",
        "remedies": [
            "Drink warm water frequently.",
            "Try warm salt-water gargling.",
            "Avoid dust, smoke, perfume, and cold drinks.",
            "Use steam inhalation if there is congestion.",
            "Rest your voice if throat irritation is present."
        ],
        "advice": [
            "Consult a doctor if cough lasts more than a week, has blood, high fever, chest pain, or breathing difficulty.",
            SAFETY_LINE
        ]
    },
    {
        "name": "Acidity / Indigestion",
        "symptoms": ["acidity", "stomach_pain", "vomiting"],
        "strong_symptoms": ["acidity"],
        "severity": "Low to Moderate",
        "remedies": [
            "Eat small and light meals.",
            "Avoid spicy, oily, fried, and very late-night food.",
            "Do not lie down immediately after eating.",
            "Drink water and avoid excess tea, coffee, and carbonated drinks.",
            "Keep a gap between dinner and sleep."
        ],
        "advice": [
            "Consult a doctor if stomach pain is severe, repeated, or comes with vomiting blood, black stool, weight loss, or chest discomfort.",
            SAFETY_LINE
        ]
    },
    {
        "name": "Diarrhea / Stomach Infection",
        "symptoms": ["diarrhea", "stomach_pain", "vomiting", "fever", "fatigue"],
        "strong_symptoms": ["diarrhea"],
        "severity": "Moderate",
        "remedies": [
            "Drink ORS or fluids to prevent dehydration.",
            "Eat light food such as rice, curd, banana, or plain food if tolerated.",
            "Avoid oily, spicy, and outside food.",
            "Wash hands properly and maintain hygiene.",
            "Take rest."
        ],
        "advice": [
            "Seek medical care if there is blood in stool, severe dehydration, high fever, repeated vomiting, or diarrhea lasting more than 1–2 days.",
            SAFETY_LINE
        ]
    },
    {
        "name": "Nausea / Vomiting",
        "symptoms": ["vomiting", "stomach_pain", "dizziness", "fatigue"],
        "strong_symptoms": ["vomiting"],
        "severity": "Moderate",
        "remedies": [
            "Take small sips of water or ORS.",
            "Avoid heavy, oily, and spicy food.",
            "Eat small portions when vomiting reduces.",
            "Rest in a comfortable position.",
            "Avoid strong smells that trigger nausea."
        ],
        "advice": [
            "Seek medical care if vomiting is repeated, contains blood, causes dehydration, or is associated with severe stomach pain or confusion.",
            SAFETY_LINE
        ]
    },
    {
        "name": "Headache / Fatigue",
        "symptoms": ["headache", "fatigue", "dizziness", "body_pain", "fever"],
        "strong_symptoms": ["headache"],
        "severity": "Low to Moderate",
        "remedies": [
            "Drink water and avoid dehydration.",
            "Rest in a quiet and comfortable place.",
            "Reduce screen brightness and avoid loud noise.",
            "Eat on time if headache is related to skipping meals.",
            "Sleep properly."
        ],
        "advice": [
            "Seek medical help if headache is sudden and severe, occurs with fever and stiff neck, confusion, weakness, vomiting, or vision changes.",
            SAFETY_LINE
        ]
    },
    {
        "name": "Allergy / Skin Irritation",
        "symptoms": ["allergy", "cold", "cough"],
        "strong_symptoms": ["allergy"],
        "severity": "Low to Moderate",
        "remedies": [
            "Avoid the suspected trigger such as dust, food, cosmetics, or pollen.",
            "Keep the affected skin clean and avoid scratching.",
            "Use a cool compress for itching if comfortable.",
            "Avoid strong perfumes, dust, and smoke.",
            "Wear loose, comfortable clothing if skin irritation is present."
        ],
        "advice": [
            "Seek urgent help if allergy comes with swelling of lips/face, breathing difficulty, dizziness, or fainting.",
            SAFETY_LINE
        ]
    }
]


# -------------------------------------------------
# SCORING ENGINE
# -------------------------------------------------

def score_condition(detected_symptoms, condition):
    score = 0

    condition_symptoms = condition.get("symptoms", [])
    strong_symptoms = condition.get("strong_symptoms", [])

    for symptom in detected_symptoms:
        if symptom in condition_symptoms:
            score += 1

        if symptom in strong_symptoms:
            score += 2

    total_possible = len(condition_symptoms) + len(strong_symptoms) * 2

    return score, total_possible


def get_best_condition(detected_symptoms):
    best_condition = None
    best_score = 0
    best_total = 1

    for condition in CONDITIONS:
        score, total = score_condition(detected_symptoms, condition)

        if score > best_score:
            best_score = score
            best_total = total
            best_condition = condition

    return best_condition, best_score, best_total


def generate_low_confidence_response(symptom_text, detected_symptoms):
    readable_symptoms = ", ".join(detected_symptoms) if detected_symptoms else "not clearly identified"

    return {
        "predicted_disease": "Symptoms not clear enough",
        "confidence": 35,
        "severity": "Unknown",
        "remedies": [
            "Please enter more specific symptoms.",
            "Mention duration, severity, temperature if fever is present, and any associated symptoms.",
            "Drink water, rest, and avoid self-medication until the symptoms are clearer."
        ],
        "advice": [
            f"Detected symptom keywords: {readable_symptoms}.",
            "Example input: fever with cough and throat pain for 2 days.",
            SAFETY_LINE
        ]
    }


# -------------------------------------------------
# MAIN FUNCTION USED BY VIEW
# -------------------------------------------------

def predict_disease(symptoms):
    symptom_text = normalize_text(symptoms)

    if not symptom_text:
        return {
            "predicted_disease": "No symptoms entered",
            "confidence": 0,
            "severity": "Unknown",
            "remedies": [
                "Please enter your symptoms to get general remedy guidance."
            ],
            "advice": [
                SAFETY_LINE
            ]
        }

    emergency_result = check_emergency(symptom_text)

    if emergency_result.get("is_emergency"):
        return emergency_result

    detected_symptoms = extract_symptom_labels(symptom_text)

    if not detected_symptoms:
        return generate_low_confidence_response(symptom_text, detected_symptoms)

    best_condition, score, total = get_best_condition(detected_symptoms)

    if not best_condition or score <= 0:
        return generate_low_confidence_response(symptom_text, detected_symptoms)

    confidence = format_confidence(score, total)

    if confidence < 35:
        return generate_low_confidence_response(symptom_text, detected_symptoms)

    severity = best_condition.get("severity", "Moderate")

    if "fever" in detected_symptoms and len(detected_symptoms) >= 3:
        severity = "Moderate"

    if "diarrhea" in detected_symptoms and "vomiting" in detected_symptoms:
        severity = "Moderate to High"

    if "dizziness" in detected_symptoms and "vomiting" in detected_symptoms:
        severity = "Moderate to High"

    return {
        "predicted_disease": best_condition.get("name", "General illness"),
        "confidence": confidence,
        "severity": severity,
        "remedies": best_condition.get("remedies", []),
        "advice": best_condition.get("advice", []),
    }