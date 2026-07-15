import csv
from pathlib import Path
from functools import lru_cache
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

BASE_DIR = Path(__file__).resolve().parents[3]

DATASET_FILES = [
    BASE_DIR / "apps" / "prescription" / "dataset" / "medicine_database.csv",
    BASE_DIR / "apps" / "datasets" / "symcat.csv",
    BASE_DIR / "apps" / "report_summarizer" / "datasets" / "health_indicators.csv",
]


@lru_cache(maxsize=1)
def build_knowledge_base():
    documents = []

    for path in DATASET_FILES:
        if not path.exists():
            continue

        with open(path, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            for row in reader:
                text = " ".join(str(value) for value in row.values() if value)
                if text.strip():
                    documents.append({
                        "source": path.name,
                        "text": text.strip()
                    })

    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform([doc["text"] for doc in documents])

    return documents, vectorizer, matrix


def retrieve_context(query, top_k=3):
    documents, vectorizer, matrix = build_knowledge_base()

    if not documents:
        return "No local knowledge base available."

    query_vector = vectorizer.transform([query])
    scores = cosine_similarity(query_vector, matrix).flatten()

    top_indexes = scores.argsort()[-top_k:][::-1]

    results = []

    for index in top_indexes:
        if scores[index] <= 0:
            continue

        doc = documents[index]
        results.append(f"Source: {doc['source']}\n{doc['text']}")

    return "\n\n".join(results) if results else "No relevant local context found."