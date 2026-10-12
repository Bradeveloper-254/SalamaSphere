from rest_framework import serializers

from .models import ThreatAssessment


ALLOWED_INDICATORS = {
    "immediate_danger",
    "serious_threat",
    "credible_threat",
    "coercion",
    "repeated_harassment",
    "inappropriate_behavior",
}


class ThreatAssessmentCreateSerializer(serializers.Serializer):

    user_selected_level = serializers.ChoiceField(
        choices=["low", "medium", "high"],
        required=False,
        allow_null=True,
    )

    indicators = serializers.DictField(
        child=serializers.BooleanField(),
        required=False,
    )

    user_explanation = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=3000,
    )

    def validate_indicators(self, value):
        unknown_keys = set(value.keys()) - ALLOWED_INDICATORS

        if unknown_keys:
            raise serializers.ValidationError(
                "One or more indicator names are not supported."
            )

        return value


class ThreatAssessmentReviewSerializer(serializers.Serializer):

    action = serializers.ChoiceField(
        choices=[
            "accept",
            "correct",
            "mark_incorrect",
        ]
    )

    corrected_level = serializers.ChoiceField(
        choices=["low", "medium", "high"],
        required=False,
    )

    explanation = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=3000,
    )

    def validate(self, attrs):
        action = attrs["action"]

        if (
            action == "correct"
            and not attrs.get("corrected_level")
        ):
            raise serializers.ValidationError({
                "corrected_level": (
                    "Provide the corrected threat level."
                )
            })

        return attrs