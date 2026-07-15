import pandas as pd


class DatasetEngine:

    def __init__(self):

        try:

            self.df = pd.read_csv(
                "datasets/symcat.csv"
            )

        except:

            self.df = None


    def predict(self, profile):

        if self.df is None:

            return {

                "condition":
                "No dataset loaded",

                "confidence":
                0
            }

        score = 0

        if profile.glucose > 140:
            score += 30

        if profile.bmi > 30:
            score += 30

        if profile.sleep_hours < 6:
            score += 20

        if profile.heart_rate > 100:
            score += 20

        if score < 30:

            disease = (
                "Healthy Pattern"
            )

        elif score < 60:

            disease = (
                "Metabolic Risk"
            )

        else:

            disease = (
                "High Risk Condition"
            )

        return {

            "condition":
            disease,

            "confidence":
            score
        }