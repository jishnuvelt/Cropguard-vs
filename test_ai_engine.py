from app.ai_engine import analyze_case


def test_detect_powdery_mildew() -> None:
    result = analyze_case(
        symptoms="White powder on leaves and stems, moderate spread",
        crop_name="Grapes",
        filename="leaf.jpg",
    )
    assert result["disease"] == "Powdery Mildew"
    assert result["confidence"] >= 0.67
    assert result["severity"] >= 5


def test_unknown_case_escalates() -> None:
    result = analyze_case(
        symptoms="Plant showing unusual pattern without clear lesions",
        crop_name="Tomato",
        filename="unknown.jpg",
    )
    assert result["needs_expert"] is True
