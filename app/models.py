import uuid
from typing import Literal

from pydantic import BaseModel, HttpUrl


class Texture(BaseModel):
    id: uuid.UUID
    state: Literal["ACTIVE", "INACTIVE"]
    url: HttpUrl


class Skin(Texture):
    variant: Literal["CLASSIC", "SLIM"]


class Cape(Texture):
    alias: str


class MinecraftProfile(BaseModel):
    id: uuid.UUID
    name: str
    skins: list[Skin]
    capes: list[Cape]
