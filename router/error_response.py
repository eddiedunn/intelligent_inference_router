from typing import List, Optional, Any, Dict
from pydantic import BaseModel

class ErrorDetail(BaseModel):
    loc: List[Any]
    msg: str
    type: str
    ctx: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    type: str
    code: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    param: Optional[str] = None
    trace_id: Optional[str] = None

    class Config:
        schema_extra = {
            "example": {
                "type": "validation_error",
                "code": "invalid_payload",
                "message": "Request payload validation failed.",
                "details": [
                    {
                        "loc": ["body", "model"],
                        "msg": "Field required",
                        "type": "missing"
                    }
                ],
                "param": "model",
                "trace_id": "abc123-xyz"
            }
        }
