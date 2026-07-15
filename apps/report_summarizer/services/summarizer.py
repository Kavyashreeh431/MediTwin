import os
import re
import pandas as pd


BASE_DIR = os.path.dirname(
    os.path.dirname(__file__)
)

CSV_PATH = os.path.join(
    BASE_DIR,
    "datasets",
    "health_indicators.csv"
)


def normalize_space(text):

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def load_dataset():

    if not os.path.exists(CSV_PATH):
        return pd.DataFrame()

    return pd.read_csv(CSV_PATH)


def safe_text(value, default=""):

    if pd.isna(value):
        return default

    return str(value)


def detect_patient(text):

    patient_match = re.search(
        r"(\d{1,3})\s*Y\s*/\s*(Male|Female)",
        text,
        re.IGNORECASE
    )

    age = "NA"
    gender = "NA"

    if patient_match:

        age = patient_match.group(1)

        gender = patient_match.group(2).title()

    patient_type = "Adult"

    if age != "NA" and int(age) < 18:

        patient_type = "Child"

    pregnancy_terms = [
        "patient is pregnant",
        "pregnant patient",
        "antenatal",
        "gestational age",
        "trimester"
    ]

    lowered = text.lower()

    if any(term in lowered for term in pregnancy_terms):

        patient_type = "Pregnant"

    return age, gender, patient_type


def find_indicator_row(dataset, test_name):

    test_name_lower = test_name.lower()

    for _, row in dataset.iterrows():

        test = safe_text(
            row.get("test_name", "")
        ).lower()

        aliases = safe_text(
            row.get("aliases", "")
        ).lower().split("|")

        all_names = [test] + [
            a.strip()
            for a in aliases
            if a.strip()
        ]

        if test_name_lower in all_names:

            return row

    return None


def get_range_columns(patient_type):

    if patient_type == "Pregnant":
        return "pregnant_low", "pregnant_high"

    if patient_type == "Child":
        return "child_low", "child_high"

    return "adult_low", "adult_high"


def get_lines(text):

    lines = []

    for line in text.splitlines():

        cleaned = normalize_space(line)

        if cleaned:
            lines.append(cleaned)

    return lines


def should_skip_line(line):

    noise_words = [
        "reference",
        "biological ref",
        "comments",
        "interpretation",
        "verified",
        "important instructions",
        "end of report",
        "page",
        "print report"
    ]

    lowered = line.lower()

    return any(word in lowered for word in noise_words)


def extract_number_after_alias_from_line(line, aliases):

    for alias in aliases:

        pattern = re.compile(
            re.escape(alias),
            re.IGNORECASE
        )

        match = pattern.search(line)

        if not match:
            continue

        after = line[match.end():]

        after = re.split(
            r"(reference|biological ref|normal range|comments|verified|interpretation)",
            after,
            flags=re.IGNORECASE
        )[0]

        numbers = re.findall(
            r"\b\d+(?:\.\d+)?\b",
            after
        )

        if numbers:
            return numbers[0]

    return None


def extract_numeric_value(text, aliases, exclude_terms=None):

    if exclude_terms is None:
        exclude_terms = []

    lines = get_lines(text)

    # First try line-wise extraction
    for line in lines:

        if should_skip_line(line):
            continue

        lowered = line.lower()

        if any(term.lower() in lowered for term in exclude_terms):
            continue

        if not any(alias.lower() in lowered for alias in aliases):
            continue

        value = extract_number_after_alias_from_line(
            line,
            aliases
        )

        if value:
            return float(value)

    # Fallback for flattened PDF text
    flat = normalize_space(text)

    for alias in aliases:

        match = re.search(
            re.escape(alias),
            flat,
            re.IGNORECASE
        )

        if not match:
            continue

        start = match.start()
        end = match.end()

        nearby = flat[max(0, start - 60): end + 180]
        nearby_lower = nearby.lower()

        if any(term.lower() in nearby_lower for term in exclude_terms):
            continue

        after = flat[end:end + 180]

        after = re.split(
            r"(reference|biological ref|normal range|comments|verified|interpretation)",
            after,
            flags=re.IGNORECASE
        )[0]

        numbers = re.findall(
            r"\b\d+(?:\.\d+)?\b",
            after
        )

        if numbers:
            return float(numbers[0])

    return None


def extract_presence_value(text, aliases):

    lines = get_lines(text)

    keywords = [
        "Present(+)",
        "Present",
        "Absent",
        "Negative",
        "Positive",
        "Normal"
    ]

    for line in lines:

        lowered = line.lower()

        if not any(alias.lower() in lowered for alias in aliases):
            continue

        for key in keywords:

            if key.lower() in lowered:
                return key

    return None

def is_valid_numeric_value(test_name, value):

    valid_ranges = {
        "HbA1c": (2, 20),
        "Estimated Average Glucose": (30, 600),
        "Fasting Glucose": (30, 600),
        "Hemoglobin": (3, 25),
        "TSH": (0.001, 100),
        "T3": (10, 500),
        "T4": (0.1, 30),
        "TSH": (0.001, 100),
        "Free T3": (0.1, 30),
        "Free T4": (0.1, 10),
        "Cholesterol": (50, 500),
        "Triglycerides": (20, 1000),
        "Creatinine": (0.1, 20),
        "Urea": (1, 300),
        "ALT": (1, 2000),
        "AST": (1, 2000),
        "CRP": (0, 500),
        "ESR": (0, 150),
        "Pus Cells": (0, 500),
        "RBC": (0, 500),
        "Epithelial Cells": (0, 500),
    }

    if test_name not in valid_ranges:
        return True

    low, high = valid_ranges[test_name]

    return low <= value <= high

def extract_report_values(text):

    values = {}

    flat_text = normalize_space(text)

    special_patterns = {
        "HbA1c": [
            r"HbA1c(?:(?!Reference|Biological|Normal Range|Comment|Interpretation).){0,150}?(\d+(?:\.\d+)?)\s*%"
        ],

        "Estimated Average Glucose": [
            r"Estimated\s+Average\s+Glucose(?:(?!Reference|Biological|Normal Range|Comment|Interpretation).){0,180}?(\d+(?:\.\d+)?)",
            r"\beAG\b(?:(?!Reference|Biological|Normal Range|Comment|Interpretation).){0,180}?(\d+(?:\.\d+)?)"
        ],

        "CRP": [
            r"(?:CRP|C\s*Reactive\s*Protein|C-Reactive Protein)(?:(?!Reference|Biological|Normal Range|Comment|Interpretation).){0,150}?(\d+(?:\.\d+)?)\s*(?:mg/L|mg/dL|mg)?"
        ],

        "ESR": [
            r"(?:ESR|Erythrocyte\s+Sedimentation\s+Rate)(?:(?!Reference|Biological|Normal Range|Comment|Interpretation).){0,120}?(\d+(?:\.\d+)?)"
        ],

        "Pus Cells": [
            r"Pus\s*cells(?:(?!Reference|Biological|Normal Range|Comment|Interpretation).){0,120}?(\d+)"
        ],

        "RBC": [
            r"\bRBC\b(?:(?!Reference|Biological|Normal Range|Comment|Interpretation).){0,120}?(\d+)"
        ],

        "Epithelial Cells": [
            r"Epithelial\s+Cells(?:(?!Reference|Biological|Normal Range|Comment|Interpretation).){0,150}?(\d+)",
            r"Epithelial\s+Cell(?:(?!Reference|Biological|Normal Range|Comment|Interpretation).){0,150}?(\d+)"
        ],
        "TSH": [
    r"(?:\bTSH\b|Thyroid\s+Stimulating\s+Hormone)"
    r"(?:(?!Reference|Biological|Normal Range|Comment|Interpretation).){0,150}?"
    r"(\d+(?:\.\d+)?)"
        ],

        "Free T3": [
            r"(?:Free\s*T3|\bFT3\b)"
            r"(?:(?!Reference|Biological|Normal Range|Comment|Interpretation).){0,150}?"
            r"(\d+(?:\.\d+)?)"
        ],

        "Free T4": [
            r"(?:Free\s*T4|\bFT4\b)"
            r"(?:(?!Reference|Biological|Normal Range|Comment|Interpretation).){0,150}?"
            r"(\d+(?:\.\d+)?)"
        ],

        "T3": [
            r"(?:Total\s*T3|\bT3\b|Triiodothyronine)"
            r"(?:(?!Reference|Biological|Normal Range|Comment|Interpretation).){0,150}?"
            r"(\d+(?:\.\d+)?)"
        ],

        "T4": [
            r"(?:Total\s*T4|\bT4\b|Thyroxine)"
            r"(?:(?!Reference|Biological|Normal Range|Comment|Interpretation).){0,150}?"
            r"(\d+(?:\.\d+)?)"
        ],
    }

    for test_name, patterns in special_patterns.items():

        for pattern in patterns:

            match = re.search(
                pattern,
                flat_text,
                re.IGNORECASE | re.DOTALL
            )

            if match:

                value = float(match.group(1))

                if is_valid_numeric_value(test_name, value):

                    values[test_name] = value

                    print("DETECTED:", test_name, value)

                else:

                    print("SKIPPED INVALID:", test_name, value)

                break

    bacteria_match = re.search(
        r"Bacteria(?:(?!Reference|Biological|Normal Range|Comment|Interpretation).){0,150}?"
        r"(Present\(\+\)|Present|Absent|Negative|Positive)",
        flat_text,
        re.IGNORECASE | re.DOTALL
    )

    if bacteria_match:

        values["Bacteria"] = bacteria_match.group(1)

        print("DETECTED: Bacteria", values["Bacteria"])

    urine_glucose_match = re.search(
        r"(?:Urine\s+Glucose|Glucose\s+Oxidase|Glucose)"
        r"(?:(?!Reference|Biological|Normal Range|Comment|Interpretation).){0,150}?"
        r"(Negative|Positive|Present|Absent)",
        flat_text,
        re.IGNORECASE | re.DOTALL
    )

    if urine_glucose_match:

        values["Urine Glucose"] = urine_glucose_match.group(1)

        print("DETECTED: Urine Glucose", values["Urine Glucose"])

    protein_match = re.search(
        r"(?:Proteins?|Urine\s+Protein)"
        r"(?:(?!Reference|Biological|Normal Range|Comment|Interpretation).){0,150}?"
        r"(Negative|Positive|Present|Absent)",
        flat_text,
        re.IGNORECASE | re.DOTALL
    )

    if protein_match:

        values["Protein"] = protein_match.group(1)

        print("DETECTED: Protein", values["Protein"])

    return values

def interpret_value(test_name, value, row, patient_type):

    unit = safe_text(
        row.get("unit", "")
    )

    if isinstance(value, str):

        value_lower = value.lower()

        if value_lower in [
            "negative",
            "absent",
            "normal"
        ]:

            return {
                "status": "normal",
                "line": f"✅ {test_name}: {value}",
                "meaning": safe_text(
                    row.get("normal_interpretation"),
                    "Good indicator."
                )
            }

        return {
            "status": "abnormal",
            "line": f"⚠️ {test_name}: {value}",
            "meaning": safe_text(
                row.get("high_interpretation"),
                "Needs clinical attention."
            )
        }

    low_col, high_col = get_range_columns(
        patient_type
    )

    try:

        low = float(row.get(low_col, 0))

        high = float(row.get(high_col, 0))

    except Exception:

        low = 0

        high = 0

    if value < low:

        return {
            "status": "abnormal",
            "line": f"⚠️ {test_name}: {value} {unit}",
            "meaning": safe_text(
                row.get("low_interpretation"),
                "Below reference range."
            )
        }

    if value > high:

        return {
            "status": "abnormal",
            "line": f"🔴 {test_name}: {value} {unit}",
            "meaning": safe_text(
                row.get("high_interpretation"),
                "Above reference range."
            )
        }

    return {
        "status": "normal",
        "line": f"✅ {test_name}: {value} {unit}",
        "meaning": safe_text(
            row.get("normal_interpretation"),
            "Good indicator."
        )
    }


def summarize(text):

    if not text:
        return "No report text found."

    dataset = load_dataset()

    if dataset.empty:

        return (
            "Health indicator dataset not found. "
            "Please add health_indicators.csv."
        )

    age, gender, patient_type = detect_patient(
        text
    )

    values = extract_report_values(
        text
    )

    normal = []

    abnormal = []

    for test_name, value in values.items():

        row = find_indicator_row(
            dataset,
            test_name
        )

        if row is None:

            continue

        result = interpret_value(
            test_name,
            value,
            row,
            patient_type
        )

        block = (
            f"{result['line']}\n"
            f"Interpretation: {result['meaning']}"
        )

        if result["status"] == "normal":

            normal.append(block)

        else:

            abnormal.append(block)

    output = []

    output.append(
        "📋 AI Clinical Report Interpretation"
    )

    output.append(
        f"👤 Patient Profile\n"
        f"• Age: {age} Years\n"
        f"• Gender: {gender}\n"
        f"• Patient Type: {patient_type}"
    )

    output.append(
        "━━━━━━━━━━━━━━━━━━"
    )

    output.append(
        "🟢 Key Normal Findings"
    )

    if normal:

        output.extend(normal)

    else:

        output.append(
            "No clearly normal indicators detected."
        )

    output.append(
        "━━━━━━━━━━━━━━━━━━"
    )

    output.append(
        "🟡 Findings Requiring Observation"
    )

    if abnormal:

        output.extend(abnormal)

    else:

        output.append(
            "No abnormal indicators detected."
        )

    output.append(
        "━━━━━━━━━━━━━━━━━━"
    )

    output.append(
        "🏥 Diagnostic Impression"
    )

    if len(abnormal) == 0:

        output.append(
            "Overall laboratory indicators appear largely normal."
        )

        overall = "🟢 GOOD"

        risk = "LOW"

    elif len(abnormal) <= 2:

        output.append(
            "Mild abnormalities are present. Clinical correlation is recommended."
        )

        overall = "🟡 NEEDS OBSERVATION"

        risk = "MODERATE"

    else:

        output.append(
            "Multiple abnormal indicators are present. Medical review is recommended."
        )

        overall = "🔴 ATTENTION REQUIRED"

        risk = "HIGH"

    output.append(
        "━━━━━━━━━━━━━━━━━━"
    )

    output.append(
        "💡 Clinical Recommendations"
    )

    if abnormal:

        output.append(
            "• Review abnormal values with a healthcare professional.\n"
            "• Monitor symptoms related to abnormal findings.\n"
            "• Repeat testing if advised by the physician."
        )

    else:

        output.append(
            "• Maintain healthy lifestyle habits.\n"
            "• Continue routine health monitoring.\n"
            "• Consult a physician if symptoms are present."
        )

    output.append(
        "━━━━━━━━━━━━━━━━━━"
    )

    output.append(
        f"🧭 Overall Health Indicator\n"
        f"{overall}\n\n"
        f"Risk Level: {risk}"
    )

    output.append(
        "Note: This AI summary is informational and does not replace medical diagnosis."
    )

    return "\n\n".join(
        str(item)
        for item in output
    )