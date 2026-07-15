import os
import re
import csv
import shutil
from difflib import SequenceMatcher


# -------------------------------------------------
# OPTIONAL RXNORM IMPORT
# -------------------------------------------------

try:
    from .rxnorm_service import get_rxnorm_info
except Exception as e:
    print("RxNorm service import failed:", e)

    def get_rxnorm_info(medicine_name, ingredients=""):
        return {
            "rxnorm_id": "Not available",
            "rxnorm_name": "Not available",
            "rxnorm_tty": "Not available",
            "rxnorm_synonym": "Not available",
            "rxnorm_language": "Not available",
            "rxnorm_suppress": "Not available",
            "rxnorm_match_term": "Not available",
            "rxnorm_source": "Local dataset only"
        }


# -------------------------------------------------
# OPTIONAL LLM IMPORT
# -------------------------------------------------

try:
    from .llm_engine import extract_prescription_items_with_llm
except Exception as e:
    print("LLM engine import failed:", e)

    def extract_prescription_items_with_llm(prescription_text):
        return []


# -------------------------------------------------
# OPTIONAL TROCR IMPORT
# -------------------------------------------------

try:
    from .tocr_engine import extract_trocr_text_from_file, TROCR_AVAILABLE
except Exception as e:
    print("TrOCR engine import failed:", e)
    TROCR_AVAILABLE = False

    def extract_trocr_text_from_file(image_file):
        return ""


# -------------------------------------------------
# OPTIONAL OCR IMPORTS
# -------------------------------------------------

try:
    import cv2
    import numpy as np
    import pytesseract
    OCR_AVAILABLE = True
except Exception as e:
    print("OCR import error:", e)
    OCR_AVAILABLE = False


try:
    import easyocr
    EASYOCR_AVAILABLE = True
except Exception as e:
    print("EasyOCR import error:", e)
    EASYOCR_AVAILABLE = False


try:
    import fitz
except Exception:
    fitz = None


BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# -------------------------------------------------
# BASIC HELPERS
# -------------------------------------------------

def clean_text(text):
    if not text:
        return ""

    text = str(text)
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)

    return text.strip()


def compact_text(text):
    if not text:
        return ""

    text = str(text)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_key(value):
    if not value:
        return ""

    value = str(value).lower().strip()
    value = value.replace("_", "-")
    value = re.sub(r"[^a-z0-9\-\s]", " ", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_search_text(value):
    value = normalize_key(value)
    value = value.replace(".", " ")
    value = value.replace(",", " ")
    value = value.replace("(", " ")
    value = value.replace(")", " ")
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def similarity(a, b):
    a = normalize_key(a)
    b = normalize_key(b)

    if not a or not b:
        return 0

    return SequenceMatcher(None, a, b).ratio()


def text_contains_term(text, term):
    if not text or not term:
        return False, -1

    text = normalize_search_text(text)
    term = normalize_search_text(term)

    if not text or not term:
        return False, -1

    pattern = r"(?<![a-zA-Z0-9])" + re.escape(term) + r"(?![a-zA-Z0-9])"
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        return True, match.start()

    return False, -1


def safe_value(value, fallback="Not clearly mentioned"):
    if value is None:
        return fallback

    value = str(value).strip()

    if not value:
        return fallback

    return value


def is_clear_value(value):
    if value is None:
        return False

    value = str(value).strip().lower()

    unclear_values = [
        "",
        "not clearly mentioned",
        "not mentioned",
        "missing",
        "unknown",
        "none",
        "null",
        "n/a",
    ]

    return value not in unclear_values


def use_llm_value_only_if_clear(llm_value, detected_value):
    if is_clear_value(llm_value):
        return str(llm_value).strip()

    return detected_value


# -------------------------------------------------
# MEDICINE DATASET LOADER
# -------------------------------------------------

MEDICINE_DB = {}
MEDICINE_SEARCH_TERMS = {}


def get_csv_value(row, field_name, default=""):
    for key, value in row.items():
        if key and key.strip().lower() == field_name.lower():
            if value is None:
                return default
            return str(value).strip()

    return default


def add_search_term(term, medicine_key):
    term = normalize_key(term)

    if not term:
        return

    cleaned_terms = set()

    cleaned_terms.add(term)
    cleaned_terms.add(term.replace("-", " "))
    cleaned_terms.add(term.replace(" ", "-"))
    cleaned_terms.add(term.replace("-", ""))
    cleaned_terms.add(term.replace(" ", ""))

    removed_form = re.sub(
        r"\b(tablet|tab|capsule|cap|syrup|syp|injection|inj|drops|drop|cream|ointment)\b",
        "",
        term,
        flags=re.IGNORECASE
    )

    removed_form = re.sub(r"\s+", " ", removed_form).strip()

    if removed_form:
        cleaned_terms.add(removed_form)
        cleaned_terms.add(removed_form.replace("-", " "))
        cleaned_terms.add(removed_form.replace(" ", "-"))
        cleaned_terms.add(removed_form.replace("-", ""))
        cleaned_terms.add(removed_form.replace(" ", ""))

    for item in cleaned_terms:
        item = normalize_key(item)

        if item:
            MEDICINE_SEARCH_TERMS[item] = medicine_key


def load_medicine_database():
    global MEDICINE_DB, MEDICINE_SEARCH_TERMS

    MEDICINE_DB = {}
    MEDICINE_SEARCH_TERMS = {}

    dataset_path = os.path.join(
        BASE_DIR,
        "dataset",
        "medicine_database.csv"
    )

    print("Medicine CSV path:", dataset_path)

    if not os.path.exists(dataset_path):
        print("Medicine database CSV not found:", dataset_path)
        return

    try:
        with open(dataset_path, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            print("Medicine CSV headers:", reader.fieldnames)

            for row in reader:
                key = normalize_key(get_csv_value(row, "key"))

                if not key:
                    continue

                aliases = get_csv_value(row, "aliases", "")
                alias_list = []

                if aliases:
                    alias_list = [
                        normalize_key(alias)
                        for alias in re.split(r"[|,;/]+", aliases)
                        if normalize_key(alias)
                    ]

                medicine_data = {
                    "display_name": get_csv_value(row, "display_name", key) or key,
                    "aliases": alias_list,
                    "ingredients": get_csv_value(row, "ingredients", "Not available") or "Not available",
                    "purpose": get_csv_value(row, "purpose", "Not available") or "Not available",
                    "common_dosage": get_csv_value(row, "common_dosage", "Use only as prescribed.") or "Use only as prescribed.",
                    "common_frequency": get_csv_value(row, "common_frequency", "Follow doctor's prescription.") or "Follow doctor's prescription.",
                    "side_effects": get_csv_value(row, "side_effects", "Not available") or "Not available",
                    "warnings": get_csv_value(row, "warnings", "Consult doctor/pharmacist before use.") or "Consult doctor/pharmacist before use.",
                    "avoid_if": get_csv_value(row, "avoid_if", "Avoid if allergic to this medicine.") or "Avoid if allergic to this medicine.",

                    "rxnorm_id": get_csv_value(row, "rxnorm_id", ""),
                    "rxnorm_name": get_csv_value(row, "rxnorm_name", ""),
                    "drug_class": get_csv_value(row, "drug_class", "Not available") or "Not available",
                    "dosage_form": get_csv_value(row, "dosage_form", "Not available") or "Not available",
                    "route": get_csv_value(row, "route", "Not available") or "Not available",
                    "strength": get_csv_value(row, "strength", "Not available") or "Not available",
                }

                MEDICINE_DB[key] = medicine_data

                add_search_term(key, key)

                display_name = get_csv_value(row, "display_name", "")

                if display_name:
                    add_search_term(display_name, key)
                    add_search_term(display_name.split("/")[0].strip(), key)

                for alias in alias_list:
                    add_search_term(alias, key)

        print("Medicine database loaded:", len(MEDICINE_DB))
        print("Medicine search terms loaded:", len(MEDICINE_SEARCH_TERMS))
        print("Medicine keys sample:", list(MEDICINE_DB.keys())[:10])

    except Exception as e:
        print("Medicine database loading error:", e)


load_medicine_database()


# -------------------------------------------------
# MEDICINE MATCHING
# -------------------------------------------------

def normalize_drug_candidate(name):
    if not name:
        return ""

    name = str(name).strip()

    name = re.sub(
        r"\b(tab|tablet|cap|capsule|syp|syrup|inj|injection|drop|drops|cream|ointment|rx)\b",
        "",
        name,
        flags=re.IGNORECASE
    )

    name = re.split(
        r"\b(\d+\s*(mg|ml|mcg|g|iu|units)|od|bd|tds|qid|hs|sos|once|twice|daily|morning|night|after|before|for|days|day|week|weeks|month|months)\b",
        name,
        flags=re.IGNORECASE
    )[0]

    name = re.sub(r"[^A-Za-z0-9\- ]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()

    return normalize_key(name)


def correct_common_medicine_spelling(candidate):
    if not candidate:
        return ""

    cleaned = normalize_key(candidate)

    spelling_fixes = {
        "azythromycin": "azithromycin",
        "azithromicin": "azithromycin",
        "azithromycine": "azithromycin",
        "azytrhomycin": "azithromycin",
        "azithro": "azithromycin",

        "paracetmol": "paracetamol",
        "paracitamol": "paracetamol",
        "pracetamol": "paracetamol",

        "cetrizine": "cetirizine",
        "cetrizin": "cetirizine",
        "cetrezine": "cetirizine",

        "amoxcillin": "amoxicillin",
        "amoxycillin": "amoxicillin",

        "metformn": "metformin",
        "metfornin": "metformin",

        "pantocd": "pantocid",
        "pantacid": "pantocid",
    }

    return spelling_fixes.get(cleaned, cleaned)


def find_medicine_from_dataset(candidate):
    load_medicine_database()

    raw_candidate = str(candidate or "").strip()

    if not raw_candidate:
        return None, None

    print("FIND MEDICINE RAW:", raw_candidate)

    possible_candidates = set()

    possible_candidates.add(raw_candidate)
    possible_candidates.add(normalize_key(raw_candidate))
    possible_candidates.add(normalize_drug_candidate(raw_candidate))

    corrected_candidate = correct_common_medicine_spelling(raw_candidate)

    if corrected_candidate:
        possible_candidates.add(corrected_candidate)

    simple_words = re.findall(
        r"[A-Za-z][A-Za-z0-9\-]{2,40}",
        raw_candidate.lower()
    )

    for word in simple_words:
        possible_candidates.add(word)
        possible_candidates.add(normalize_drug_candidate(word))
        possible_candidates.add(correct_common_medicine_spelling(word))

    for candidate_item in possible_candidates:
        key = normalize_key(candidate_item)

        if not key:
            continue

        possible_keys = [
            key,
            key.replace("-", " "),
            key.replace(" ", "-"),
            key.replace("-", ""),
            key.replace(" ", ""),
        ]

        for item in possible_keys:
            if item in MEDICINE_DB:
                print("MATCHED DIRECT DB:", item)
                return item, MEDICINE_DB[item]

        for item in possible_keys:
            if item in MEDICINE_SEARCH_TERMS:
                medicine_key = MEDICINE_SEARCH_TERMS[item]
                print("MATCHED SEARCH TERM:", item, "=>", medicine_key)
                return medicine_key, MEDICINE_DB.get(medicine_key)

    best_key = None
    best_term = None
    best_score = 0

    normalized_candidate = normalize_key(raw_candidate)

    if len(normalized_candidate) < 4:
        return None, None

    for term, medicine_key in MEDICINE_SEARCH_TERMS.items():
        clean_term = normalize_key(term)

        if len(clean_term) < 4:
            continue

        score = similarity(normalized_candidate, clean_term)

        if score > best_score:
            best_score = score
            best_key = medicine_key
            best_term = clean_term

    print("BEST FUZZY MATCH:", best_term, "=>", best_key, "score:", best_score)

    if best_key and best_score >= 0.78:
        print("MATCHED FUZZY:", raw_candidate, "=>", best_key)
        return best_key, MEDICINE_DB.get(best_key)

    return None, None


def split_prescription_items(text):
    if not text:
        return []

    text = clean_text(text)

    text = re.sub(
        r"\b(Tab|Tablet|Cap|Capsule|Syp|Syrup|Inj|Injection|Drop|Drops|Cream|Ointment)\.?\s+",
        r"\n\1 ",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"\b\d+\)\s*",
        "\n",
        text
    )

    parts = re.split(r"[\n;,]+", text)

    final_parts = []

    for part in parts:
        part = compact_text(part)

        if len(part) >= 3:
            final_parts.append(part)

    return final_parts


def extract_candidate_medicines(text):
    if not text:
        return []

    load_medicine_database()

    candidates = []
    cleaned_text = clean_text(text)

    for key, medicine_data in MEDICINE_DB.items():
        search_terms = [key]

        display_name = medicine_data.get("display_name", "")

        if display_name:
            search_terms.append(display_name)
            search_terms.append(display_name.split("/")[0].strip())

        aliases = medicine_data.get("aliases", [])

        if isinstance(aliases, list):
            search_terms.extend(aliases)

        for term in search_terms:
            found, _ = text_contains_term(cleaned_text, term)

            if found:
                candidates.append(term)
                break

    words = re.findall(r"\b[A-Za-z][A-Za-z0-9\-]{3,40}\b", cleaned_text)

    ignore_words = {
        "tablet", "tab", "capsule", "cap", "syrup", "syp", "injection", "inj",
        "morning", "night", "evening", "daily", "days", "day", "after", "before",
        "food", "dose", "take", "once", "twice", "thrice", "times", "with",
        "without", "doctor", "patient", "name", "age", "male", "female",
        "prescription", "medicine", "medicines", "diagnosis", "complaint",
    }

    for word in words:
        word_clean = word.strip()
        normalized_word = normalize_key(word_clean)

        if normalized_word not in ignore_words:
            candidates.append(word_clean)

    final_candidates = []
    seen = set()

    for candidate in candidates:
        key = normalize_key(candidate)

        if key and key not in seen:
            seen.add(key)
            final_candidates.append(candidate)

    print("DETECTED CANDIDATE MEDICINES:", final_candidates)

    return final_candidates


def find_item_for_medicine(text, medicine_key, medicine_data=None):
    items = split_prescription_items(text)

    search_terms = []

    if medicine_key:
        search_terms.append(medicine_key)

    if medicine_data:
        display_name = medicine_data.get("display_name", "")

        if display_name:
            search_terms.append(display_name)
            search_terms.append(display_name.split("/")[0].strip())

        aliases = medicine_data.get("aliases", [])

        if isinstance(aliases, list):
            search_terms.extend(aliases)

    for item in items:
        for term in search_terms:
            found, _ = text_contains_term(item, term)

            if found:
                return item

    return text


# -------------------------------------------------
# TESSERACT CONFIGURATION
# -------------------------------------------------

TESSERACT_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Users\kavya\AppData\Local\Programs\Tesseract-OCR\tesseract.exe",
]

TESSERACT_FOUND = False

if OCR_AVAILABLE:
    system_tesseract = shutil.which("tesseract")

    if system_tesseract:
        pytesseract.pytesseract.tesseract_cmd = system_tesseract
        TESSERACT_FOUND = True
        print("Tesseract found from PATH:", system_tesseract)

    else:
        for path in TESSERACT_CANDIDATES:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                TESSERACT_FOUND = True
                print("Tesseract found at:", path)
                break

if not TESSERACT_FOUND:
    print("Tesseract OCR not found. Tesseract fallback will not work.")


# -------------------------------------------------
# EASYOCR CONFIGURATION
# -------------------------------------------------

EASYOCR_READER = None

if EASYOCR_AVAILABLE:
    try:
        EASYOCR_READER = easyocr.Reader(["en"], gpu=False)
        print("EasyOCR loaded successfully.")
    except Exception as e:
        EASYOCR_READER = None
        print("EasyOCR loading failed:", e)
else:
    print("EasyOCR not installed. Handwriting OCR will be limited.")


# -------------------------------------------------
# PDF EXTRACTION
# -------------------------------------------------

def extract_pdf_text(pdf_file):
    if fitz is None:
        print("PyMuPDF not installed. PDF extraction unavailable.")
        return ""

    try:
        pdf_file.seek(0)
        pdf_bytes = pdf_file.read()

        doc = fitz.open(
            stream=pdf_bytes,
            filetype="pdf"
        )

        text = ""

        for page in doc:
            text += page.get_text("text") + "\n"

        doc.close()

        print("PDF Extracted Text:")
        print(text)

        return text.strip()

    except Exception as e:
        print("PDF extraction error:", e)
        return ""


# -------------------------------------------------
# IMAGE OCR
# -------------------------------------------------

def preprocess_image_for_ocr(image_file):
    if not OCR_AVAILABLE:
        print("OCR libraries not installed.")
        return []

    try:
        image_file.seek(0)

        file_bytes = np.frombuffer(
            image_file.read(),
            np.uint8
        )

        image = cv2.imdecode(
            file_bytes,
            cv2.IMREAD_COLOR
        )

        if image is None:
            print("Image decode failed.")
            return []

        variants = []

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        gray_big = cv2.resize(
            gray,
            None,
            fx=3,
            fy=3,
            interpolation=cv2.INTER_CUBIC
        )

        variants.append(("gray_big", gray_big))

        blur = cv2.medianBlur(gray_big, 3)

        otsu = cv2.threshold(
            blur,
            0,
            255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )[1]

        variants.append(("otsu", otsu))

        adaptive = cv2.adaptiveThreshold(
            blur,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11
        )

        variants.append(("adaptive", adaptive))

        inverted = cv2.bitwise_not(adaptive)
        variants.append(("inverted", inverted))

        debug_path = os.path.join(
            BASE_DIR,
            "ocr_debug_output.png"
        )

        cv2.imwrite(debug_path, adaptive)
        print("Saved OCR debug image:", debug_path)

        return variants

    except Exception as e:
        print("Image preprocessing error:", e)
        return []


def extract_image_text(image_file):
    final_text_parts = []

    try:
        if TROCR_AVAILABLE:
            image_file.seek(0)

            trocr_text = extract_trocr_text_from_file(image_file)

            if trocr_text and trocr_text.strip():
                print("-------- TROCR START --------")
                print(trocr_text)
                print("--------- TROCR END ---------")

                final_text_parts.append(trocr_text.strip())

    except Exception as e:
        print("TrOCR extraction error:", e)

    try:
        if EASYOCR_READER is not None and OCR_AVAILABLE:
            image_file.seek(0)

            file_bytes = np.frombuffer(
                image_file.read(),
                np.uint8
            )

            image = cv2.imdecode(
                file_bytes,
                cv2.IMREAD_COLOR
            )

            if image is not None:
                easy_results = EASYOCR_READER.readtext(image)

                easy_text = "\n".join(
                    item[1] for item in easy_results
                    if len(item) >= 2
                )

                print("-------- EASYOCR START --------")
                print(easy_text)
                print("--------- EASYOCR END ---------")

                if easy_text.strip():
                    final_text_parts.append(easy_text.strip())

    except Exception as e:
        print("EasyOCR extraction error:", e)

    try:
        if OCR_AVAILABLE and TESSERACT_FOUND:
            image_file.seek(0)

            variants = preprocess_image_for_ocr(image_file)

            configs = [
                "--oem 3 --psm 6",
                "--oem 3 --psm 11",
                "--oem 3 --psm 4",
                "--oem 3 --psm 12",
            ]

            best_tesseract_text = ""

            for variant_name, processed_image in variants:
                for config in configs:
                    text = pytesseract.image_to_string(
                        processed_image,
                        config=config
                    )

                    print("OCR output using:", variant_name, config)
                    print("-------- TESSERACT START --------")
                    print(text)
                    print("--------- TESSERACT END ---------")

                    if len(text.strip()) > len(best_tesseract_text.strip()):
                        best_tesseract_text = text

            if best_tesseract_text.strip():
                final_text_parts.append(best_tesseract_text.strip())

    except Exception as e:
        print("Tesseract extraction error:", e)

    combined_text = "\n".join(final_text_parts)
    combined_text = clean_text(combined_text)

    print("-------- FINAL COMBINED OCR TEXT --------")
    print(combined_text)
    print("--------- FINAL COMBINED OCR END --------")

    return combined_text


def extract_prescription_text(uploaded_file=None, manual_text=""):
    if manual_text and manual_text.strip():
        return manual_text.strip()

    if not uploaded_file:
        return ""

    file_name = uploaded_file.name.lower()

    print("Uploaded prescription file:", file_name)

    if file_name.endswith(".pdf"):
        return extract_pdf_text(uploaded_file)

    if file_name.endswith((".jpg", ".jpeg", ".png", ".webp")):
        return extract_image_text(uploaded_file)

    return ""


# -------------------------------------------------
# OCR QUALITY CHECK
# -------------------------------------------------

def has_prescription_signal(text):
    lower_text = compact_text(text).lower()

    signal_patterns = [
        r"\btab\b",
        r"\btablet\b",
        r"\bcap\b",
        r"\bcapsule\b",
        r"\bsyp\b",
        r"\bsyrup\b",
        r"\binj\b",
        r"\binjection\b",
        r"\bmg\b",
        r"\bml\b",
        r"\bod\b",
        r"\bbd\b",
        r"\btds\b",
        r"\bdaily\b",
        r"\bdays\b",
        r"\bonce\b",
        r"\btwice\b",
        r"\bmorning\b",
        r"\bnight\b",
        r"\bafter food\b",
        r"\bbefore food\b",
    ]

    for pattern in signal_patterns:
        if re.search(pattern, lower_text, re.IGNORECASE):
            return True

    return False


def is_bad_ocr_text(text):
    if not text:
        return True

    flat = compact_text(text)
    words = re.findall(r"[A-Za-z0-9\-]+", flat)

    if len(words) < 1:
        return True

    short_words = [
        word for word in words
        if len(word) <= 3
    ]

    short_ratio = len(short_words) / max(len(words), 1)

    if len(words) > 40 and short_ratio > 0.60 and not has_prescription_signal(text):
        return True

    return False


# -------------------------------------------------
# DOSAGE / FREQUENCY / DURATION
# -------------------------------------------------

def extract_dosage_from_text(text):
    match = re.search(
        r"(\d+\s?(?:mg|ml|mcg|g|iu|units))",
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return "Not clearly mentioned"


def normalize_frequency(freq):
    if not freq:
        return "Not clearly mentioned"

    value = freq.upper().strip()

    mapping = {
        "OD": "Once daily",
        "BD": "Twice daily",
        "TDS": "Three times daily",
        "QID": "Four times daily",
        "HS": "At night",
        "SOS": "When needed",
        "1-0-0": "Morning only",
        "0-1-0": "Afternoon only",
        "0-0-1": "Night only",
        "1-0-1": "Morning and night",
        "1-1-1": "Morning, afternoon, and night",
        "ONCE DAILY": "Once daily",
        "TWICE DAILY": "Twice daily",
        "THRICE DAILY": "Three times daily",
        "THREE TIMES DAILY": "Three times daily",
    }

    return mapping.get(value, freq)


def extract_frequency_from_text(text):
    frequency_patterns = [
        r"\b(OD|BD|TDS|QID|HS|SOS)\b",
        r"\b(1-0-0|0-1-0|0-0-1|1-0-1|1-1-1)\b",
        r"\b(once daily)\b",
        r"\b(twice daily)\b",
        r"\b(thrice daily)\b",
        r"\b(three times daily)\b",
        r"\b(morning)\b",
        r"\b(night)\b",
        r"\b(evening)\b",
        r"\b(after food)\b",
        r"\b(before food)\b",
    ]

    for pattern in frequency_patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            return normalize_frequency(match.group(1))

    return "Not clearly mentioned"


def extract_duration_from_text(text):
    match = re.search(
        r"(\d+\s?(?:days|day|weeks|week|months|month))",
        text,
        re.IGNORECASE
    )

    if match:
        return match.group(1)

    return "Not clearly mentioned"


# -------------------------------------------------
# ANALYSIS BUILDERS
# -------------------------------------------------

def build_dataset_medicine_analysis(text, medicine_key, medicine_data, llm_item=None):
    medicine_line = find_item_for_medicine(
        text,
        medicine_key,
        medicine_data
    )

    print("MEDICINE LINE USED:", medicine_line)

    dosage = extract_dosage_from_text(medicine_line)
    frequency = extract_frequency_from_text(medicine_line)
    duration = extract_duration_from_text(medicine_line)

    print("REGEX DOSAGE:", dosage)
    print("REGEX FREQUENCY:", frequency)
    print("REGEX DURATION:", duration)

    if llm_item is not None and isinstance(llm_item, dict):
        print("LLM ITEM:", llm_item)

        dosage = use_llm_value_only_if_clear(
            llm_item.get("dosage"),
            dosage
        )

        frequency = use_llm_value_only_if_clear(
            llm_item.get("frequency"),
            frequency
        )

        duration = use_llm_value_only_if_clear(
            llm_item.get("duration"),
            duration
        )

        confidence = "LLM/dataset medicine match"

    else:
        confidence = "Dataset medicine match"

    display_name = medicine_data.get("display_name", medicine_key)
    ingredients = medicine_data.get("ingredients", "")

    rxnorm_info = get_rxnorm_info(display_name, ingredients)

    dataset_rxnorm_id = str(medicine_data.get("rxnorm_id", "")).strip()
    dataset_rxnorm_name = str(medicine_data.get("rxnorm_name", "")).strip()

    if dataset_rxnorm_id:
        rxnorm_info["rxnorm_id"] = dataset_rxnorm_id
        rxnorm_info["rxnorm_source"] = "Local dataset"

    if dataset_rxnorm_name:
        rxnorm_info["rxnorm_name"] = dataset_rxnorm_name

    return {
        "medicine_name": display_name,
        "matched_name": medicine_key,
        "confidence": confidence,

        "rxnorm_id": rxnorm_info.get("rxnorm_id", "Not available"),
        "rxnorm_name": rxnorm_info.get("rxnorm_name", "Not available"),
        "rxnorm_tty": rxnorm_info.get("rxnorm_tty", "Not available"),
        "rxnorm_synonym": rxnorm_info.get("rxnorm_synonym", "Not available"),
        "rxnorm_language": rxnorm_info.get("rxnorm_language", "Not available"),
        "rxnorm_suppress": rxnorm_info.get("rxnorm_suppress", "Not available"),
        "rxnorm_match_term": rxnorm_info.get("rxnorm_match_term", "Not available"),
        "rxnorm_source": rxnorm_info.get("rxnorm_source", "Local dataset only"),

        "dosage": dosage,
        "frequency": frequency,
        "duration": duration,

        "ingredients": medicine_data.get("ingredients", "Not available"),
        "drug_class": medicine_data.get("drug_class", "Not available"),
        "dosage_form": medicine_data.get("dosage_form", "Not available"),
        "route": medicine_data.get("route", "Not available"),
        "strength": medicine_data.get("strength", "Not available"),

        "purpose": medicine_data.get("purpose", "Not available"),
        "common_dosage": medicine_data.get("common_dosage", "Use only as prescribed."),
        "common_frequency": medicine_data.get("common_frequency", "Follow doctor's prescription."),
        "side_effects": medicine_data.get("side_effects", "Not available"),
        "warnings": medicine_data.get("warnings", "Consult doctor/pharmacist before use."),
        "avoid_if": medicine_data.get("avoid_if", "Avoid if allergic to this medicine."),
    }


def build_unknown_medicine_analysis(llm_item):
    medicine_name = safe_value(
        llm_item.get("medicine_name"),
        "Unknown medicine"
    )

    rxnorm_info = get_rxnorm_info(medicine_name)

    return {
        "medicine_name": medicine_name,
        "matched_name": medicine_name,
        "confidence": "LLM extracted, but not found in medicine dataset",

        "rxnorm_id": rxnorm_info.get("rxnorm_id", "Not available"),
        "rxnorm_name": rxnorm_info.get("rxnorm_name", "Not available"),
        "rxnorm_tty": rxnorm_info.get("rxnorm_tty", "Not available"),
        "rxnorm_synonym": rxnorm_info.get("rxnorm_synonym", "Not available"),
        "rxnorm_language": rxnorm_info.get("rxnorm_language", "Not available"),
        "rxnorm_suppress": rxnorm_info.get("rxnorm_suppress", "Not available"),
        "rxnorm_match_term": rxnorm_info.get("rxnorm_match_term", "Not available"),
        "rxnorm_source": rxnorm_info.get("rxnorm_source", "RxNav API / Not found"),

        "dosage": safe_value(llm_item.get("dosage")),
        "frequency": safe_value(llm_item.get("frequency")),
        "duration": safe_value(llm_item.get("duration")),

        "ingredients": "Not available",
        "drug_class": "Not available",
        "dosage_form": "Not available",
        "route": "Not available",
        "strength": "Not available",

        "purpose": "Not available. Add this medicine to medicine_database.csv.",
        "common_dosage": "Use only as prescribed by the doctor.",
        "common_frequency": "Follow doctor's prescription.",
        "side_effects": "Not available in local dataset.",
        "warnings": "Medicine not verified in dataset. Confirm with doctor or pharmacist.",
        "avoid_if": "Avoid if allergic. Confirm with doctor or pharmacist.",
    }


# -------------------------------------------------
# MAIN FUNCTION
# -------------------------------------------------

def analyze_prescription(uploaded_file=None, manual_text=""):
    load_medicine_database()

    extracted_text = extract_prescription_text(
        uploaded_file,
        manual_text
    )

    text = clean_text(extracted_text)

    if not text:
        return {
            "status": "error",
            "message": (
                "No readable prescription text found. "
                "Upload a clearer image or type the prescription manually."
            ),
            "text": "",
            "medicines": [],
            "warnings": [
                "Doctor handwriting can be difficult for OCR.",
                "Use a clear, well-lit, straight image.",
                "For safety, manually verify medicine names before using the analysis."
            ]
        }

    if is_bad_ocr_text(text):
        return {
            "status": "error",
            "message": (
                "OCR could not read the prescription clearly. "
                "Please upload a clearer image or type the medicine name manually."
            ),
            "text": text,
            "medicines": [],
            "warnings": [
                "The uploaded image produced unreadable OCR text.",
                "Use a straight, close, well-lit image.",
                "Crop only the prescription area.",
                "For doctor handwriting, manual correction may be required.",
                "Do not rely on unclear OCR for medicine decisions."
            ]
        }

    analyzed_medicines = []
    warnings = []
    seen_keys = set()
    unknown_llm_items = []

    llm_items = extract_prescription_items_with_llm(text)

    if llm_items:
        print("Using LLM extracted medicines")

        for item in llm_items:
            if not isinstance(item, dict):
                continue

            medicine_name = item.get("medicine_name", "")

            print("LLM MEDICINE NAME:", medicine_name)

            medicine_key, medicine_data = find_medicine_from_dataset(medicine_name)

            print("LLM MATCH RESULT:", medicine_key, medicine_data is not None)

            if medicine_data:
                if medicine_key in seen_keys:
                    continue

                analysis = build_dataset_medicine_analysis(
                    text,
                    medicine_key,
                    medicine_data,
                    llm_item=item
                )

                analyzed_medicines.append(analysis)
                seen_keys.add(medicine_key)

                warnings.append(
                    f"{analysis['medicine_name']}: {analysis['warnings']}"
                )

            else:
                unknown_llm_items.append(item)

    print("Running dataset fallback also to find remaining medicines.")

    candidates = extract_candidate_medicines(text)

    for candidate in candidates:
        medicine_key, medicine_data = find_medicine_from_dataset(candidate)

        if not medicine_data:
            continue

        if medicine_key in seen_keys:
            continue

        print("ANALYZING EXTRA MEDICINE FROM DATASET:", medicine_key)

        analysis = build_dataset_medicine_analysis(
            text,
            medicine_key,
            medicine_data,
            llm_item=None
        )

        analyzed_medicines.append(analysis)
        seen_keys.add(medicine_key)

        warnings.append(
            f"{analysis['medicine_name']}: {analysis['warnings']}"
        )

    for item in unknown_llm_items:
        medicine_name = item.get("medicine_name", "")
        unknown_key = normalize_key(medicine_name)

        if not unknown_key:
            continue

        if unknown_key in seen_keys:
            continue

        analysis = build_unknown_medicine_analysis(item)
        analyzed_medicines.append(analysis)
        seen_keys.add(unknown_key)

        warnings.append(
            f"{analysis['medicine_name']}: {analysis['warnings']}"
        )

    if not analyzed_medicines:
        return {
            "status": "not_found",
            "message": (
                "Text was extracted, but no medicine names were confidently detected."
            ),
            "text": text,
            "medicines": [],
            "warnings": [
                "Check the extracted text below.",
                "If OCR is wrong, type the prescription manually and analyze again.",
                "Make sure medicines exist in medicine_database.csv.",
                "Add OCR spelling mistakes as aliases in the CSV.",
                "Manual verification is required for handwritten prescriptions."
            ]
        }

    print("TOTAL ANALYZED MEDICINES:", len(analyzed_medicines))

    return {
        "status": "success",
        "message": "Prescription analyzed using local LLM, medicine dataset, and RxNorm lookup when available.",
        "text": text,
        "medicines": analyzed_medicines,
        "warnings": warnings
    }