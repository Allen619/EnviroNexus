from pydantic import BaseModel


class FactorQueryRequest(BaseModel):
    query: str
