def get_recommendation(disease):

    recommendations = {

        "Influenza":
        """
        • Rest
        • Drink fluids
        • Monitor fever
        • Seek doctor if severe
        """,

        "Migraine":
        """
        • Hydrate
        • Reduce screen time
        • Rest
        """,

        "Common Cold":
        """
        • Warm liquids
        • Sleep well
        • Steam inhalation
        """,

        "Gastritis":
        """
        • Avoid spicy food
        • Eat light meals
        """
    }

    return recommendations.get(
        disease,
        "Consult healthcare professional"
    )