from django import forms


class SymptomForm(forms.Form):

    symptoms = forms.CharField(

        widget=forms.Textarea(

            attrs={

                "class":
                "form-control",

                "rows":
                5
            }

        )

    )