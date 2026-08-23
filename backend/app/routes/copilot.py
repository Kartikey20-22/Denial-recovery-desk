from fastapi import APIRouter, Depends

from app.ai.copilot import CopilotRequest, CopilotResponse, chat
from app.security import current_user

r = APIRouter()


@r.post("/chat", response_model=CopilotResponse)
async def copilot_chat(payload: CopilotRequest, u=Depends(current_user)):
    return await chat(payload)


@r.get("/examples")
async def copilot_examples(u=Depends(current_user)):
    return {
        "examples": [
            "What evidence supports an appeal for CLM-1001?",
            "What is missing before we submit CLM-1005?",
            "Explain the payer policy for a prior authorization denial.",
            "Which cases look like duplicate claims?",
            "How much was recovered for CLM-1011?",
        ]
    }
