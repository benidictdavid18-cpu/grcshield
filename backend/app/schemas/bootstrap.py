from pydantic import BaseModel
class BootstrapOut(BaseModel):
    status: str
    reason: str
    disclaimer: str = "Sample / Portfolio Assessment"
