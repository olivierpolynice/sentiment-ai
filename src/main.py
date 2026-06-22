from fastapi import FastAPI
# Application principale FastAPI utilisée par Jenkins pour tester le pipeline CI/CD
app = FastAPI(title="SentimentAI", version="0.1.0")
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
