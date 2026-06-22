from fastapi import FastAPI

from src.model import SentimentModel
from src.schemas import PredictionRequest, PredictionResponse

app = FastAPI(title="SentimentAI", version="0.1.0")

model = SentimentModel()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    return model.predict(request.text)
