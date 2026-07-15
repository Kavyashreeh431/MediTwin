import requests
from functools import lru_cache


RXNAV_BASE_URL = "https://rxnav.nlm.nih.gov/REST"


def safe_text(value, fallback="Not available"):
    if value is None:
        return fallback

    value = str(value).strip()

    if not value:
        return fallback

    return value


def get_single_rxnorm_result(search_term):
    if not search_term:
        return None

    try:
        response = requests.get(
            f"{RXNAV_BASE_URL}/rxcui.json",
            params={
                "name": search_term,
                "search": "2"
            },
            timeout=8
        )

        if response.status_code != 200:
            return None

        data = response.json()
        rxnorm_ids = data.get("idGroup", {}).get("rxnormId", [])

        if not rxnorm_ids:
            return None

        rxnorm_id = rxnorm_ids[0]

        property_response = requests.get(
            f"{RXNAV_BASE_URL}/rxcui/{rxnorm_id}/properties.json",
            timeout=8
        )

        if property_response.status_code != 200:
            return {
                "rxnorm_id": rxnorm_id,
                "rxnorm_name": search_term,
                "rxnorm_tty": "Not available",
                "rxnorm_synonym": "Not available",
                "rxnorm_language": "Not available",
                "rxnorm_suppress": "Not available",
                "rxnorm_match_term": search_term,
                "rxnorm_source": "RxNav API"
            }

        property_data = property_response.json()
        properties = property_data.get("properties", {})

        return {
            "rxnorm_id": safe_text(properties.get("rxcui"), rxnorm_id),
            "rxnorm_name": safe_text(properties.get("name"), search_term),
            "rxnorm_tty": safe_text(properties.get("tty")),
            "rxnorm_synonym": safe_text(properties.get("synonym")),
            "rxnorm_language": safe_text(properties.get("language")),
            "rxnorm_suppress": safe_text(properties.get("suppress")),
            "rxnorm_match_term": search_term,
            "rxnorm_source": "RxNav API"
        }

    except Exception as e:
        print("RxNorm API error:", e)
        return None


@lru_cache(maxsize=300)
def get_rxnorm_info(medicine_name, ingredients=""):
    default_result = {
        "rxnorm_id": "Not available",
        "rxnorm_name": "Not available",
        "rxnorm_tty": "Not available",
        "rxnorm_synonym": "Not available",
        "rxnorm_language": "Not available",
        "rxnorm_suppress": "Not available",
        "rxnorm_match_term": "Not available",
        "rxnorm_source": "Local dataset only"
    }

    search_terms = []

    if medicine_name:
        search_terms.append(str(medicine_name).strip())

    if ingredients:
        ingredient_text = str(ingredients)
        ingredient_text = ingredient_text.replace("/", ",")
        ingredient_text = ingredient_text.replace("+", ",")

        for item in ingredient_text.split(","):
            item = item.strip()

            if item:
                search_terms.append(item)

    seen = set()
    final_terms = []

    for term in search_terms:
        cleaned = term.strip().lower()

        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            final_terms.append(term.strip())

    for term in final_terms:
        result = get_single_rxnorm_result(term)

        if result and result.get("rxnorm_id") != "Not available":
            return result

    return default_result