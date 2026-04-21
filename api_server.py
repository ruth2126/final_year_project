import os
import torch
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModelForSeq2SeqLM

app = FastAPI(title="Mental Health Support API")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MENTAL_MODEL_PATH = os.path.join(BASE_DIR, "mentalbert")
FLAN_MODEL_PATH = os.path.join(BASE_DIR, "flan_t5")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

mental_tokenizer = None
mental_model = None
flan_tokenizer = None
flan_model = None


class InputText(BaseModel):
    text: str


@app.on_event("startup")
def load_models():
    global mental_tokenizer, mental_model, flan_tokenizer, flan_model

    print("Loading models...")

    mental_tokenizer = AutoTokenizer.from_pretrained(MENTAL_MODEL_PATH)
    mental_model = AutoModelForSequenceClassification.from_pretrained(
        MENTAL_MODEL_PATH
    ).to(device)

    flan_tokenizer = AutoTokenizer.from_pretrained(FLAN_MODEL_PATH)
    flan_model = AutoModelForSeq2SeqLM.from_pretrained(
        FLAN_MODEL_PATH
    ).to(device)

    mental_model.eval()
    flan_model.eval()

    print("Models loaded successfully.")


def classify(text):
    with torch.no_grad():
        inputs = mental_tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=128
        )

        inputs = {k: v.to(device) for k, v in inputs.items()}

        outputs = mental_model(**inputs)

        probs = torch.softmax(outputs.logits, dim=1)
        score = probs[0][1].item()

        label = "Distress" if score >= 0.5 else "No Distress"

        return label, round(score, 4)


def generate(text):
    prompt = f"Provide calm, supportive advice for this concern:\n{text}"

    with torch.no_grad():
        inputs = flan_tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=256
        )

        inputs = {k: v.to(device) for k, v in inputs.items()}

        outputs = flan_model.generate(
            **inputs,
            max_length=120,
            do_sample=True,
            temperature=0.7
        )

        return flan_tokenizer.decode(
            outputs[0],
            skip_special_tokens=True
        ).strip()


def full_pipeline(text):
    prediction, confidence = classify(text)
    advice = generate(text)

    return {
        "prediction": prediction,
        "confidence": confidence,
        "advice": advice
    }


@app.get("/")
def home():
    return {"message": "API is running"}


@app.post("/analyze")
def analyze(data: InputText):
    return full_pipeline(data.text)
