from pydantic import BaseModel, Field

class Login(BaseModel):
    email:str
    password:str
class Register(BaseModel):
    email:str
    password:str=Field(min_length=8)
    name:str
class Review(BaseModel):
    decision:str
    notes:str=""
    edited_draft:str|None=None
class WorkflowDecision(BaseModel):
    decision:str  # APPROVE | EDIT | REQUEST_MORE_EVIDENCE | REJECT
    notes:str=""
    edited_draft:str|None=None
