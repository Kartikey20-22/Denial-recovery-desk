from pathlib import Path

def retrieve(query:str)->str:
    base=Path("data")
    hits=[]
    for p in base.rglob("*.txt"):
        text=p.read_text(errors="ignore")
        score=sum(w in text.lower() for w in query.lower().split() if len(w)>4)
        if score: hits.append((score,p.name,text))
    hits.sort(reverse=True)
    return "\n\n".join(f"[{n}]\n{t[:2500]}" for _,n,t in hits[:4])
