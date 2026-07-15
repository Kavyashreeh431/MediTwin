from .dataset_engine import DatasetEngine
from .recommendations import RecommendationEngine


class DigitalTwin:

    def __init__(self, profile):

        self.profile = profile


    def build(self):

        dataset = DatasetEngine()

        prediction = dataset.predict(
            self.profile
        )

        recommendation = (
            RecommendationEngine()
        )

        return {

            "risk":
            self.calculate_risk(),

            "health_score":
            max(
                100 -
                prediction[
                    "confidence"
                ],
                10
            ),

            "prediction_confidence":
            prediction[
                "confidence"
            ],

            "dataset_condition":
            prediction[
                "condition"
            ],

            "recommendations":

            recommendation.generate(

                self.profile,

                prediction[
                    "condition"
                ]

            ),

            "explanations":

            self.explain()
        }


    def calculate_risk(self):

        if self.profile.glucose > 180:

            return "High"

        elif self.profile.glucose > 120:

            return "Moderate"

        return "Low"


    def explain(self):

        e = []

        if self.profile.glucose > 140:
            e.append(
                "Elevated glucose"
            )

        if self.profile.bmi > 30:
            e.append(
                "High BMI"
            )

        if not e:

            e.append(
                "No major indicators"
            )

        return e