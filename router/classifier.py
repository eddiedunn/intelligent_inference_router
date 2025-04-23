# Prompt classifier for IIR MVP
from transformers import pipeline
from router.settings import get_settings

settings = get_settings()
classifier = pipeline("zero-shot-classification", model=settings.classifier_model_id, device=settings.classifier_device)

async def classify_prompt(prompt: str) -> str:
    labels = ["local", "remote"]
    hypothesis_template = "This request should be handled {}."
    result = classifier(prompt, labels, hypothesis_template=hypothesis_template)
    return result["labels"][0]
