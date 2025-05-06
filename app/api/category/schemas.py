from typing import Optional
from pydantic import BaseModel, Field, conint, constr

class CategoryPredictionRequest(BaseModel):
    text: str