from django import forms

from .models import IncidentReviewNote


class IncidentReviewNoteForm(forms.ModelForm):
    class Meta:
        model = IncidentReviewNote
        fields = ["note"]

        widgets = {
            "note": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": (
                        "Enter an incident review note..."
                    ),
                    "class": "form-control",
                }
            ),
        }

    def clean_note(self):
        note = self.cleaned_data["note"].strip()

        if not note:
            raise forms.ValidationError(
                "Review notes cannot be empty."
            )

        if len(note) > 5000:
            raise forms.ValidationError(
                "Review notes cannot exceed 5000 characters."
            )

        return note