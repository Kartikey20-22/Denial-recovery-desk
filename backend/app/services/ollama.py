import json, re, httpx
from app.config import settings

SYSTEM = """You are a denial recovery assistant for a synthetic hackathon demo.
Never invent patient facts, medical facts, codes, authorizations or policies.
Classify the denial and draft an appeal using only supplied evidence.
Return ONLY JSON:
{"reason":"","code":"","confidence":0.0,"explanation":"","appeal":"","evidence":""}
Allowed reason values: coding_error, missing_prior_authorization, medical_necessity,
timely_filing, missing_documentation, eligibility, other."""

async def analyze(denial:str, context:str)->dict:
    prompt=SYSTEM+"\n\nDENIAL:\n"+denial+"\n\nREFERENCE:\n"+(context or "None")
    payload={"model":settings.ollama_model,"stream":False,
             "format":"json","options":{"temperature":0.1},
             "messages":[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}]}
    try:
        async with httpx.AsyncClient(timeout=120) as c:
            r=await c.post(settings.ollama_base_url+"/api/chat",json=payload)
            r.raise_for_status()
            raw=r.json()["message"]["content"]
            return json.loads(raw)
    except Exception:
        # deterministic demo fallback so the app remains usable if Ollama is offline
        x=denial.lower()
        if "authorization" in x or "prior auth" in x: reason,conf="missing_prior_authorization",.94
        elif "cpt" in x or "icd" in x or "coding" in x: reason,conf="coding_error",.92
        elif "medical necessity" in x: reason,conf="medical_necessity",.68
        elif "timely" in x or "filing limit" in x: reason,conf="timely_filing",.90
        elif "documentation" in x or "records" in x: reason,conf="missing_documentation",.86
        else: reason,conf="other",.55
        return {"reason":reason,"code":"","confidence":conf,
                "explanation":"Local demo fallback. Start Ollama for llama3.1:8b inference.",
                "appeal":"APPEAL DRAFT\n\nVerify all claim facts and payer policy before submission.\n\n"+denial[:1200],
                "evidence":context[:1500]}

def gate(conf:float, amount:float):
    if amount>=100000: return "HUMAN_REVIEW","High-value claim requires human approval."
    if conf>=settings.confidence_threshold: return "AUTO_READY","Confidence meets threshold."
    return "HUMAN_REVIEW","Confidence below threshold."
