import pandas as pd
import os


# ---------------------------
# LOAD DATASET
# ---------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)

DATASET = os.path.join(
    BASE_DIR,
    "datasets",
    "symcat.csv"
)

df = pd.read_csv(DATASET)

print("\nDATASET COLUMNS:")
print(df.columns.tolist())


# ---------------------------
# PREDICTION ENGINE
# ---------------------------

def predict_disease(user_input):

    user_symptoms = [

        s.strip().lower()

        for s in user_input.split(",")

        if s.strip()

    ]

    best_match = None

    best_score = 0

    # -----------------------
    # MATCH DISEASE
    # -----------------------

    for _, row in df.iterrows():

        dataset_symptoms = str(

            row.get(
                "symptom_names",
                ""
            )

        ).lower()

        matched = 0

        total = len(user_symptoms)

        for symptom in user_symptoms:

            if symptom in dataset_symptoms:

                matched += 1

        score = (

            matched / total

        ) if total else 0

        if score > best_score:

            best_score = score

            best_match = row

    # -----------------------
    # NO MATCH
    # -----------------------

    if best_match is None:

        return {

            "predicted_disease": "No disease identified",

            "confidence": 0,

            "severity": "Unknown",

            "remedies": [

                "Monitor symptoms",

                "Drink water"

            ],

            "advice": [

                "Consult healthcare provider"

            ]

        }

    # -----------------------
    # DISEASE
    # -----------------------

    disease = str(

        best_match.get(
            "condition_name",
            "Unknown"
        )

    )

    confidence = round(

        best_score * 100,

        1

    )

    # -----------------------
    # SEVERITY
    # -----------------------

    symptom_count = len(user_symptoms)

    urgent = float(
        best_match.get(
            "urgent_score",
            0
        )
    )

    if symptom_count <= 1:

        severity = "Low"

    elif symptom_count <= 3:

        severity = "Moderate"

    else:

        severity = "High"


    # Dataset urgency adjustment

    if urgent >= 0.8:

        severity = "High"

    elif urgent >= 0.4 and severity == "Low":

        severity = "Moderate"

    # -----------------------
    # REAL-TIME REMEDIES
    # -----------------------

    remedies = []

    for symptom in user_symptoms:

        if symptom == "fever":

            remedies.extend([

                "Drink fluids",

                "Take rest",

                "Monitor temperature"

            ])

        elif symptom == "cough":

            remedies.extend([

                "Steam inhalation",

                "Warm water"

            ])

        elif symptom == "vomiting":

            remedies.extend([

                "ORS solution",

                "Eat light meals"

            ])

        elif symptom == "headache":

            remedies.extend([

                "Reduce screen exposure",

                "Hydrate"

            ])

        elif symptom == "cold":

            remedies.extend([

                "Warm liquids",

                "Sleep adequately"

            ])

    if not remedies:

        remedies = [

            "Balanced diet",

            "Adequate hydration",

            "Rest"
        ]

    remedies = list(

        dict.fromkeys(remedies)

    )

    # -----------------------
    # ADVICE
    # -----------------------

    if severity == "Low":

        advice = [

            "Observe symptoms",

            "Maintain hydration"

        ]

    elif severity == "Moderate":

        advice = [

            "Reduce activity",

            "Sleep adequately"

        ]

    else:

        advice = [

            "Seek medical evaluation",

            "Avoid self medication"

        ]

    print("\nMATCHED DISEASE:", disease)

    print("CONFIDENCE:", confidence)

    print("SEVERITY:", severity)

    print("REMEDIES:", remedies)

    # -----------------------
    # RETURN
    # -----------------------

    return {

        "predicted_disease": disease,

        "confidence": confidence,

        "severity": severity,

        "remedies": remedies,

        "advice": advice

    }