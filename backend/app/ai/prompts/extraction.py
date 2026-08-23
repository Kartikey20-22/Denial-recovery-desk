from langchain_core.prompts import ChatPromptTemplate

EXTRACTION_SYSTEM = """You extract structured billing fields from a healthcare \
denial letter for a synthetic demo. This is NOT real PHI.

Rules:
- Only extract values that literally appear in the text.
- If a field is not present, leave it null/empty -- never guess or invent it.
- Never invent claim numbers, member IDs, dates, or dollar amounts.
"""

EXTRACTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", EXTRACTION_SYSTEM),
        ("human", "Denial letter / notes text:\n\n{denial_text}\n\nKnown claim number (if any): {claim_no}\n"
                  "Known payer (if any): {payer}\nKnown billed/denied amount (if any): {amount}"),
    ]
)
