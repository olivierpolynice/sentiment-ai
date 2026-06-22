from typing import Literal

from pydantic import BaseModel, Field


class PredictionRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class PredictionResponse(BaseModel):
    label: Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]
    score: float
    text: str
