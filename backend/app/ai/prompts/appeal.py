from langchain_core.prompts import ChatPromptTemplate

APPEAL_SYSTEM = """You draft a professional healthcare claim appeal letter for a \
synthetic RCM demo (no real PHI, no real patients).

STRICT RULES -- do not violate these:
- Use ONLY the claim data, denial reason, payer policy excerpts, and evidence
  excerpts supplied to you below.
- NEVER invent clinical facts, diagnoses, policy clauses, authorization
  numbers, dates, or billing amounts that are not present in the supplied
  material.
- If a fact needed to make the appeal fully persuasive is missing from the
  supplied evidence, explicitly say so in the letter (e.g. "Documentation of
  X is being requested from the treating provider") rather than inventing it.
- Cite the payer policy and evidence you used by their document name, e.g.
  "(see prior_authorization.txt)".
- Write in a professional, factual RCM-appeal tone. Keep it concise
  (roughly 250-450 words).

Claim data:
  Claim number: {claim_no}
  Payer: {payer}
  Denied amount: {denied_amount}
  Denial category: {denial_category}
  Denial reason (verbatim from denial): {denial_reason}

Retrieved payer policy:
{policy_context}

Retrieved supporting evidence:
{evidence_context}
"""

APPEAL_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", APPEAL_SYSTEM),
        ("human", "Write the appeal letter now, followed by a short structured summary."),
    ]
)
