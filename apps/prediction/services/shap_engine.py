class HealthTwin:
    def __init__(self, profile):
        self.profile = profile

    def get_value(self, field_name, default=0):
        value = getattr(self.profile, field_name, default)
        if value is None:
            return default
        return float(value)

    def get_exercise_value(self):
        """
        Supports different possible field names:
        exercise, exercise_minutes, exercise_minutes_per_week
        """
        possible_fields = [
            "exercise",
            "exercise_minutes",
            "exercise_minutes_per_week",
            "physical_activity",
        ]

        for field in possible_fields:
            if hasattr(self.profile, field):
                value = getattr(self.profile, field)
                if value is not None:
                    return float(value)

        return 0

    def explain(self):
        bmi = self.get_value("bmi")
        glucose = self.get_value("glucose")
        heart_rate = self.get_value("heart_rate")
        sleep_hours = self.get_value("sleep_hours")
        exercise = self.get_exercise_value()

        risk_points = 0
        positive_points = 0
        shap_values = []
        reasons = []

        # -------------------------------
        # BMI CHECK
        # -------------------------------
        if bmi == 0:
            risk_points += 20
            shap_values.append({
                "feature": "BMI",
                "impact": 20,
                "status": "Negative",
                "reason": "BMI not calculated."
            })
            reasons.append("BMI is not available.")

        elif bmi < 16:
            risk_points += 35
            shap_values.append({
                "feature": "BMI",
                "impact": 35,
                "status": "Negative",
                "reason": "BMI is severely underweight."
            })
            reasons.append("BMI is very low and indicates underweight.")

        elif bmi < 18.5:
            risk_points += 25
            shap_values.append({
                "feature": "BMI",
                "impact": 25,
                "status": "Negative",
                "reason": "BMI is underweight."
            })
            reasons.append("BMI is below the healthy range.")

        elif bmi < 25:
            positive_points += 25
            shap_values.append({
                "feature": "BMI",
                "impact": 25,
                "status": "Positive",
                "reason": "BMI is in the healthy range."
            })

        elif bmi < 30:
            risk_points += 20
            shap_values.append({
                "feature": "BMI",
                "impact": 20,
                "status": "Negative",
                "reason": "BMI is overweight."
            })
            reasons.append("BMI is above the healthy range.")

        else:
            risk_points += 35
            shap_values.append({
                "feature": "BMI",
                "impact": 35,
                "status": "Negative",
                "reason": "BMI is in the obesity range."
            })
            reasons.append("BMI is very high.")

        # -------------------------------
        # GLUCOSE CHECK
        # -------------------------------
        if glucose == 0:
            risk_points += 15
            shap_values.append({
                "feature": "Glucose",
                "impact": 15,
                "status": "Negative",
                "reason": "Glucose value is not available."
            })
            reasons.append("Glucose value is missing.")

        elif glucose < 70:
            risk_points += 25
            shap_values.append({
                "feature": "Glucose",
                "impact": 25,
                "status": "Negative",
                "reason": "Glucose is low."
            })
            reasons.append("Glucose level is low.")

        elif glucose <= 99:
            positive_points += 25
            shap_values.append({
                "feature": "Glucose",
                "impact": 25,
                "status": "Positive",
                "reason": "Glucose is within normal range."
            })

        elif glucose <= 125:
            risk_points += 25
            shap_values.append({
                "feature": "Glucose",
                "impact": 25,
                "status": "Negative",
                "reason": "Glucose is slightly high."
            })
            reasons.append("Glucose level is above normal range.")

        else:
            risk_points += 40
            shap_values.append({
                "feature": "Glucose",
                "impact": 40,
                "status": "Negative",
                "reason": "Glucose is high."
            })
            reasons.append("Glucose level is high.")

        # -------------------------------
        # HEART RATE CHECK
        # -------------------------------
        if heart_rate == 0:
            risk_points += 15
            shap_values.append({
                "feature": "Heart Rate",
                "impact": 15,
                "status": "Negative",
                "reason": "Heart rate is not available."
            })
            reasons.append("Heart rate value is missing.")

        elif 60 <= heart_rate <= 100:
            positive_points += 25
            shap_values.append({
                "feature": "Heart Rate",
                "impact": 25,
                "status": "Positive",
                "reason": "Heart rate is within normal range."
            })

        elif 50 <= heart_rate < 60 or 101 <= heart_rate <= 110:
            risk_points += 15
            shap_values.append({
                "feature": "Heart Rate",
                "impact": 15,
                "status": "Negative",
                "reason": "Heart rate is slightly outside normal range."
            })
            reasons.append("Heart rate is slightly outside the normal range.")

        else:
            risk_points += 30
            shap_values.append({
                "feature": "Heart Rate",
                "impact": 30,
                "status": "Negative",
                "reason": "Heart rate is outside normal range."
            })
            reasons.append("Heart rate needs attention.")

        # -------------------------------
        # SLEEP CHECK
        # -------------------------------
        if sleep_hours == 0:
            risk_points += 15
            shap_values.append({
                "feature": "Sleep Hours",
                "impact": 15,
                "status": "Negative",
                "reason": "Sleep value is not available."
            })
            reasons.append("Sleep duration is missing.")

        elif 7 <= sleep_hours <= 9:
            positive_points += 25
            shap_values.append({
                "feature": "Sleep Hours",
                "impact": 25,
                "status": "Positive",
                "reason": "Sleep duration is healthy."
            })

        elif 5 <= sleep_hours < 7 or 9 < sleep_hours <= 10:
            risk_points += 15
            shap_values.append({
                "feature": "Sleep Hours",
                "impact": 15,
                "status": "Negative",
                "reason": "Sleep duration is slightly outside recommended range."
            })
            reasons.append("Sleep duration can be improved.")

        else:
            risk_points += 30
            shap_values.append({
                "feature": "Sleep Hours",
                "impact": 30,
                "status": "Negative",
                "reason": "Sleep duration is unhealthy."
            })
            reasons.append("Sleep duration needs attention.")

        # -------------------------------
        # EXERCISE CHECK
        # Value expected: minutes per week
        # -------------------------------
        if exercise == 0:
            risk_points += 20
            shap_values.append({
                "feature": "Exercise",
                "impact": 20,
                "status": "Negative",
                "reason": "Exercise activity is missing or zero."
            })
            reasons.append("Exercise activity is low or missing.")

        elif exercise < 60:
            risk_points += 25
            shap_values.append({
                "feature": "Exercise",
                "impact": 25,
                "status": "Negative",
                "reason": "Exercise is very low."
            })
            reasons.append("Physical activity is very low.")

        elif exercise < 150:
            risk_points += 15
            shap_values.append({
                "feature": "Exercise",
                "impact": 15,
                "status": "Negative",
                "reason": "Exercise is below the recommended level."
            })
            reasons.append("Exercise duration can be improved.")

        elif exercise <= 300:
            positive_points += 20
            shap_values.append({
                "feature": "Exercise",
                "impact": 20,
                "status": "Positive",
                "reason": "Exercise duration is good."
            })

        else:
            positive_points += 20
            shap_values.append({
                "feature": "Exercise",
                "impact": 20,
                "status": "Positive",
                "reason": "Exercise level is very active."
            })

        # -------------------------------
        # FINAL SCORE
        # -------------------------------
        health_score = 100 - risk_points

        if health_score < 0:
            health_score = 0

        if risk_points >= 60:
            risk = "High"
        elif risk_points >= 25:
            risk = "Moderate"
        else:
            risk = "Low"

        confidence = min(98, 70 + positive_points - (risk_points * 0.3))
        confidence = max(55, round(confidence, 1))

        # -------------------------------
        # SUMMARY + RECOMMENDATION
        # -------------------------------
        if reasons:
            summary = "Some health indicators need attention: " + ", ".join(reasons)
        else:
            summary = "All major health indicators are within the healthy range."

        if bmi and bmi < 18.5:
            recommendation = (
                "BMI is underweight. Maintain regular meals, include nutrient-rich foods, "
                "do suitable physical activity, and consult a doctor or dietitian for healthy weight improvement."
            )
        elif exercise < 150:
            recommendation = (
                "Exercise duration is below the recommended level. Try to gradually increase physical activity "
                "with walking, stretching, or light workouts based on your health condition."
            )
        elif risk == "High":
            recommendation = (
                "Several health indicators need attention. Please consult a doctor for proper medical evaluation."
            )
        elif risk == "Moderate":
            recommendation = (
                "Some health indicators need improvement. Follow a balanced lifestyle and consult a doctor if symptoms exist."
            )
        else:
            recommendation = (
                "Good health indicators. Continue maintaining healthy food habits, proper sleep, hydration, and regular activity."
            )

        return {
            "risk": risk,
            "health_score": health_score,
            "confidence": confidence,
            "shap_values": shap_values,
            "summary": summary,
            "recommendation": recommendation,
        }