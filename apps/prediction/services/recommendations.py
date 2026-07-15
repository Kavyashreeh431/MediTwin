class RecommendationEngine:

    def generate(

        self,

        profile,

        disease

    ):

        rec = []

        if profile.sleep_hours < 7:

            rec.append(
                "Increase sleep"
            )

        if profile.glucose > 140:

            rec.append(
                "Reduce sugar intake"
            )

        if profile.bmi > 25:

            rec.append(
                "Exercise regularly"
            )

        if disease == "High Risk Condition":

            rec.append(
                "Consult healthcare professional"
            )

        if not rec:

            rec.append(
                "Maintain current lifestyle"
            )

        return rec