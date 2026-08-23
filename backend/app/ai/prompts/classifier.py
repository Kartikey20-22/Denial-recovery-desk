from langchain_core.prompts import ChatPromptTemplate

CLASSIFIER_SYSTEM = """You classify why a healthcare claim was denied, for a \
synthetic RCM demo (no real PHI). Choose exactly one category from:

PRIOR_AUTHORIZATION, MEDICAL_NECESSITY, CODING_ERROR, MISSING_DOCUMENTATION,
TIMELY_FILING, ELIGIBILITY, DUPLICATE_CLAIM, OTHER

Base your answer only on the denial text supplied. Quote the specific phrase(s)
in the denial text that justify the category as `supporting_text`. Give a
confidence between 0 and 1 reflecting how unambiguous the denial text is --
use a LOWER confidence when the wording is vague or could fit more than one
category, and reserve confidence above 0.9 for clear, unambiguous denials."""

CLASSIFIER_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", CLASSIFIER_SYSTEM),
        ("human", "Denial text:\n\n{denial_text}"),
    ]
)
