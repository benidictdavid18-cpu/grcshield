from pydantic import BaseModel, Field


class RouteIn(BaseModel):
    owner: str = Field(min_length=1, max_length=160)
    username: str
