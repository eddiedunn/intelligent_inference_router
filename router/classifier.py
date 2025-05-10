# Prompt classifier for IIR MVP
from transformers import pipeline
from router.settings import get_settings

_classifier = None

def get_classifier():
    global _classifier
    if _classifier is None:
        settings = get_settings()
        _classifier = pipeline("zero-shot-classification", model=settings.classifier_model_id, device=settings.classifier_device)
    return _classifier

async def classify_prompt(prompt: str) -> str:
    labels = ["local", "remote"]
    hypothesis_template = "This request should be handled {}."
    classifier = get_classifier()
    result = classifier(prompt, labels, hypothesis_template=hypothesis_template)
    return result["labels"][0]
