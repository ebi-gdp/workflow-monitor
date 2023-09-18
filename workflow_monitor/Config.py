from dataclasses import dataclass


@dataclass
class Config:
    callback_token: str
    namespace: str
