from __future__ import annotations

import pytest

from src import predict


EXPECTED_KEYS = {
    "predicted_label", "label_id", "offensive_score", "score_type",
    "threshold", "model_version", "warning",
}


def test_model_artifact_loads():
    model, config = predict._load_bundle()
    assert model is not None
    assert config["model_version"] == "swahili-offensive-linear-svm-clean-v1"


def test_preprocessing_replaces_invalid_surrogate_and_preserves_text():
    assert predict.preprocess_text("Habari\ud800 dada!") == "Habari\ufffd dada!"
    assert predict.preprocess_text("Usiende!") == "Usiende!"


@pytest.mark.parametrize("text", [
    "Nahitaji msaada tafadhali.",
    "Aje msee, hiyo ni noma sana.",
])
def test_valid_kiswahili_and_sheng_like_inputs_return_schema(text):
    result = predict.predict_text(text)
    assert set(result) == EXPECTED_KEYS
    assert result["predicted_label"] in {"offensive", "non_offensive"}
    assert result["label_id"] in {0, 1}
    assert isinstance(result["offensive_score"], float)
    assert "not a probability" in result["score_type"]
    assert result["warning"]


@pytest.mark.parametrize("text", [None, "", " \n\t"])
def test_empty_input_returns_no_prediction(text):
    result = predict.predict_text(text)
    assert result["predicted_label"] is None
    assert result["offensive_score"] is None
    assert result["warning"]


def test_non_string_input_is_handled():
    result = predict.predict_text(42)
    assert result["predicted_label"] is None
    assert "must be a string" in result["warning"][-1]


def test_long_input_is_truncated(monkeypatch):
    class FakeModel:
        seen = None

        def decision_function(self, values):
            self.seen = values[0]
            return [0.0]

    model = FakeModel()
    config = {"threshold": 0.0, "model_version": "test"}
    monkeypatch.setattr(predict, "_load_bundle", lambda: (model, config))
    result = predict.predict_text("a" * (predict.MAX_INPUT_CHARACTERS + 500))
    assert len(model.seen) == predict.MAX_INPUT_CHARACTERS
    assert result["label_id"] == 1
    assert any("truncated" in warning for warning in result["warning"])


def test_threshold_is_applied_to_decision_score(monkeypatch):
    class FakeModel:
        def decision_function(self, values):
            return [-0.25]

    monkeypatch.setattr(
        predict, "_load_bundle",
        lambda: (FakeModel(), {"threshold": -0.25, "model_version": "test"}),
    )
    assert predict.predict_text("message")["label_id"] == 1
    monkeypatch.setattr(
        predict, "_load_bundle",
        lambda: (FakeModel(), {"threshold": -0.24, "model_version": "test"}),
    )
    assert predict.predict_text("message")["label_id"] == 0
