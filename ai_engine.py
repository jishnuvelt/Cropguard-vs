from __future__ import annotations

from typing import Any


DISEASE_RULES = [
    {
        "disease": "Powdery Mildew",
        "keywords": ["powder", "white spot", "white layer", "dusty leaf", "fungal coat"],
        "recommendation": (
            "Remove heavily infected leaves. Apply sulfur or potassium bicarbonate spray "
            "in the early morning. Improve field ventilation and avoid overhead irrigation."
        ),
    },
    {
        "disease": "Bacterial Blight",
        "keywords": ["yellow halo", "water soaked", "leaf blight", "brown lesion", "blight"],
        "recommendation": (
            "Use certified disease-free seed and avoid excess nitrogen. Apply copper-based "
            "bactericide as per label instructions. Maintain proper plant spacing."
        ),
    },
    {
        "disease": "Leaf Rust",
        "keywords": ["rust", "orange pustule", "reddish spot", "powdery rust"],
        "recommendation": (
            "Use resistant varieties if available. Remove volunteer plants and apply "
            "triazole/strobilurin fungicide according to local agronomy guidance."
        ),
    },
    {
        "disease": "Early Blight",
        "keywords": ["target spot", "concentric ring", "lower leaf yellow", "early blight"],
        "recommendation": (
            "Prune lower affected leaves and reduce leaf wetness duration. Apply "
            "recommended protectant fungicide at 7-10 day intervals."
        ),
    },
    {
        "disease": "Nutrient Deficiency",
        "keywords": ["chlorosis", "uniform yellow", "stunted", "pale leaves", "deficiency"],
        "recommendation": (
            "Collect soil sample for testing and correct nutrient imbalance. Apply "
            "balanced NPK and micronutrient foliar feed based on crop stage."
        ),
    },
]

SEVERITY_TERMS = {
    "mild": 3,
    "minor": 3,
    "moderate": 5,
    "many": 6,
    "spreading": 7,
    "severe": 8,
    "whole field": 9,
    "wilting": 8,
    "rapid": 8,
    "drying": 7,
}


def _score_severity(text: str) -> int:
    lowered = text.lower()
    score = 4
    for term, value in SEVERITY_TERMS.items():
        if term in lowered:
            score = max(score, value)
    return min(score, 10)


def analyze_case(symptoms: str, crop_name: str, filename: str) -> dict[str, Any]:
    """
    Lightweight deterministic triage engine for MVP.
    Replace this with model inference for production deployments.
    """
    searchable_text = f"{symptoms} {crop_name} {filename}".lower()
    best_rule = None
    best_hits = 0

    for rule in DISEASE_RULES:
        hits = sum(1 for kw in rule["keywords"] if kw in searchable_text)
        if hits > best_hits:
            best_hits = hits
            best_rule = rule

    if not best_rule:
        disease = "Unknown Disease"
        confidence = 0.35
        recommendation = (
            "Image/symptom confidence is low. Keep affected plants isolated, avoid "
            "over-irrigation, and escalate to an expert for confirmed diagnosis."
        )
    else:
        disease = best_rule["disease"]
        confidence = min(0.55 + (0.12 * best_hits), 0.95)
        recommendation = best_rule["recommendation"]

    severity = _score_severity(symptoms)
    needs_expert = confidence < 0.7 or severity >= 7 or disease == "Unknown Disease"

    return {
        "disease": disease,
        "confidence": round(confidence, 2),
        "severity": severity,
        "recommendation": recommendation,
        "needs_expert": needs_expert,
    }
