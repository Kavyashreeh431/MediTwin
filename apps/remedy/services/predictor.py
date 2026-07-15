def predict_disease(symptoms):

    symptoms = symptoms.lower()

    if (
        "cough" in symptoms and
        "sore throat" in symptoms
    ):
        return "Common Cold"

    elif (
        "fever" in symptoms and
        "cough" in symptoms
    ):
        return "Influenza"

    elif (
        "headache" in symptoms
    ):
        return "Migraine"

    elif (
        "stomach" in symptoms
    ):
        return "Gastritis"

    return "General Health Issue"