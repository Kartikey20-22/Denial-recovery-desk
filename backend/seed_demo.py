import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.db import init_db,Session
from app.models import User,Claim,Denial,Payment,PayerResponse,Notification,Event,Document,ReviewTask
from app.security import hash_pw

async def main():
    await init_db()
    async with Session() as s:
        if not await s.scalar(select(User).where(User.email=="demo@denialdesk.local")):
            s.add(User(email="demo@denialdesk.local",password_hash=hash_pw("Demo@12345"),name="Priya Sharma",role="admin"))
        cases=[
          ("CLM-1001","ABC Insurance Co.",12500,"missing_prior_authorization","Prior authorization was not found for the billed service.",.94,"APPROVED",12500),
          ("CLM-1002","Star Health Insurance",8400,"coding_error","Claim denied due to CPT coding mismatch.",.91,"PENDING",0),
          ("CLM-1003","HDFC ERGO",22000,"medical_necessity","Medical necessity documentation was insufficient.",.68,"APPROVED",18000),
          ("CLM-1004","ICICI Lombard",5600,"timely_filing","Claim exceeded timely filing limit.",.55,"DENIED",0),
          ("CLM-1005","Bajaj Allianz",180000,"missing_prior_authorization","Prior authorization was not found for the billed service.",.92,"PENDING",0),
          ("CLM-1006","ABC Insurance Co.",7300,"missing_documentation","Medical records were not attached to support the claim.",.88,"APPROVED",7300),
          ("CLM-1007","Star Health Insurance",3400,"duplicate_claim","Claim identified as a duplicate of a previously processed claim.",.76,"APPROVED",3400),
          ("CLM-1008","HDFC ERGO",96000,"eligibility","Patient was not eligible for coverage on the date of service.",.48,"PENDING",0),
          ("CLM-1009","ICICI Lombard",15800,"medical_necessity","Medical necessity documentation was insufficient for the level of care billed.",.72,"APPROVED",12000),
          ("CLM-1010","Bajaj Allianz",4200,"coding_error","Claim denied due to ICD-10 and CPT code mismatch on the submitted claim.",.93,"PENDING",0),
          ("CLM-1011","ABC Insurance Co.",210000,"missing_prior_authorization","Prior authorization was not obtained before the procedure was performed.",.95,"APPROVED",175000),
          ("CLM-1012","Star Health Insurance",2100,"missing_documentation","Records were not attached to support the claim; documentation request outstanding.",.61,"PENDING",0),
          # Additional synthetic/demo cases for the AI Copilot and dashboard.
          # CLM-1013 and CLM-1014 intentionally share the same synthetic patient,
          # payer and amount to demonstrate duplicate-claim retrieval.
          ("CLM-1013","ABC Insurance Co.",7800,"duplicate_claim","Claim appears to duplicate a previously processed service for the same synthetic patient.",.89,"PENDING",0),
          ("CLM-1014","ABC Insurance Co.",7800,"duplicate_claim","Claim appears to duplicate CLM-1013 for the same synthetic patient and service date.",.93,"APPROVED",7800),
          ("CLM-1015","Star Health Insurance",14600,"coding_error","CPT 99214 was rejected because the submitted diagnosis pairing did not support the billed service.",.87,"PENDING",0),
          ("CLM-1016","Star Health Insurance",14600,"coding_error","Coding review flagged the same CPT/diagnosis pairing pattern as a prior claim.",.91,"APPROVED",14600),
          ("CLM-1017","HDFC ERGO",32000,"medical_necessity","The submitted clinical documentation did not establish the medical necessity threshold.",.64,"PENDING",0),
          ("CLM-1018","HDFC ERGO",45000,"eligibility","Coverage could not be confirmed for the date of service in the eligibility response.",.82,"APPROVED",36000),
          ("CLM-1019","ICICI Lombard",9200,"timely_filing","Payer records indicate the claim was received after the filing window.",.71,"PENDING",0),
          ("CLM-1020","Bajaj Allianz",27500,"missing_prior_authorization","Authorization reference was absent from the submitted claim packet.",.96,"APPROVED",27500),
          ("CLM-1021","ABC Insurance Co.",6100,"missing_documentation","Operative notes and discharge summary were not attached.",.58,"PENDING",0),
          ("CLM-1022","Star Health Insurance",18800,"duplicate_claim","Payer identified a duplicate line item against a previous adjudicated claim.",.79,"PENDING",0),
          ("CLM-1023","HDFC ERGO",51500,"medical_necessity","Additional clinical records are required to support the requested level of care.",.73,"PENDING",0),
          ("CLM-1024","ICICI Lombard",11800,"missing_prior_authorization","Pre-service authorization is present in the synthetic evidence archive but was not linked to the claim.",.95,"APPROVED",11800),
        ]
        existing=set((await s.scalars(select(Claim.claim_no))).all())
        for no,payer,amt,reason,text,confidence,payer_status,approved in cases:
            if no in existing: continue
            patient_ref = "PAT-DUP-013" if no in {"CLM-1013", "CLM-1014"} else f"PAT-{no[-4:]}"
            c=Claim(claim_no=no,payer=payer,amount=amt,patient_ref=patient_ref); s.add(c); await s.flush()
            d=Denial(claim_id=c.id,text=text,reason=reason,confidence=confidence,status="SUBMITTED" if payer_status != "PENDING" else "HUMAN_REVIEW"); s.add(d); await s.flush()
            if payer_status != "PENDING":
                d.submission_id=f"SIM-{no[-4:]}"; d.submitted_at=datetime.now(timezone.utc)-timedelta(days=1)
                s.add(PayerResponse(denial_id=d.id,submission_id=d.submission_id,status=payer_status,approved_amount=approved,response_reference=f"PAYER-{no[-4:]}",message=f"Demo payer response: {payer_status}."))
                if payer_status=="APPROVED":
                    paid=min(approved, amt)
                    s.add(Payment(denial_id=d.id,claim_id=c.id,payment_reference=f"PAY-{no[-4:]}",amount=paid,status="PAID",payment_date=datetime.now(timezone.utc)-timedelta(hours=2),verified=True))
                    d.outcome="COMPLETED"; d.recovered_amount=paid
                    s.add(Event(denial_id=d.id,stage="PAYMENT",status="VERIFIED",message=f"Demo payment verified: {paid:.2f}."))
            else:
                s.add(Event(denial_id=d.id,stage="HUMAN_REVIEW",status="PENDING",message="Demo case awaiting reviewer action."))
        # Expanded deterministic synthetic dataset for polished demos / buildathon judging.
        # Safe to re-run: claim numbers are unique and existing rows are skipped.
        import random
        rng = random.Random(20260823)
        payers = ["ABC Insurance Co.", "Star Health Insurance", "HDFC ERGO", "ICICI Lombard", "Bajaj Allianz", "Care Health"]
        reasons = [
            ("missing_prior_authorization", "Prior authorization was not linked to the submitted claim packet."),
            ("coding_error", "CPT and diagnosis pairing did not satisfy the payer edit."),
            ("medical_necessity", "Clinical documentation did not establish the medical necessity threshold."),
            ("timely_filing", "Payer records indicate receipt outside the timely filing window."),
            ("missing_documentation", "Required clinical records were not attached to the original claim."),
            ("eligibility", "Coverage could not be confirmed for the date of service."),
            ("duplicate_claim", "Payer identified a duplicate service or line item."),
            ("bundling", "A billed service was considered bundled into another adjudicated service."),
        ]
        first_names = ["Aarav","Vivaan","Aditya","Kabir","Arjun","Riya","Anaya","Ishita","Meera","Sara","Kavya","Nisha"]
        for i in range(1025, 1125):
            no = f"CLM-{i}"
            if no in existing: continue
            payer = rng.choice(payers)
            amount = rng.choice([3200, 4800, 6500, 7800, 9200, 12500, 14800, 18500, 24000, 31500, 42000, 56000, 78000, 125000, 185000])
            reason, text = rng.choice(reasons)
            confidence = round(rng.uniform(.46, .98), 2)
            outcome_roll = rng.random()
            if confidence >= .88 and outcome_roll < .62:
                payer_status = "APPROVED"
            elif confidence < .60 or outcome_roll < .18:
                payer_status = "PENDING"
            else:
                payer_status = "PENDING"
            c = Claim(claim_no=no, payer=payer, amount=amount, patient_ref=f"PAT-DEMO-{i}")
            s.add(c); await s.flush()
            d = Denial(claim_id=c.id, text=text, reason=reason, confidence=confidence,
                       status="SUBMITTED" if payer_status == "APPROVED" else ("HUMAN_REVIEW" if confidence < .70 else "ANALYZED"),
                       explanation=f"Synthetic demo analysis: {text} Evidence and payer policy should be validated before submission.",
                       recovery_probability=round(min(.97, max(.18, confidence * .88 + rng.uniform(-.08, .08))), 2),
                       appeal_score=round(min(98, max(52, confidence * 100 + rng.uniform(-8, 8))), 1),
                       processing_seconds=round(rng.uniform(1.8, 12.5), 2), estimated_cost_usd=round(rng.uniform(.0008, .009), 5),
                       estimated_tokens=rng.randint(850, 2600), follow_up_date=datetime.now(timezone.utc)+timedelta(days=rng.randint(3,21)))
            s.add(d); await s.flush()
            d.created_at = datetime.now(timezone.utc) - timedelta(days=rng.randint(0, 45), hours=rng.randint(0, 23))
            if payer_status == "APPROVED":
                approved = round(amount * rng.uniform(.72, 1.0), 2)
                d.submission_id = f"SIM-{i}"
                d.submitted_at = d.created_at + timedelta(hours=rng.randint(4, 48))
                s.add(PayerResponse(denial_id=d.id, submission_id=d.submission_id, status="APPROVED", approved_amount=approved,
                                    response_reference=f"PAYER-{i}", response_date=d.submitted_at+timedelta(hours=rng.randint(4, 36)),
                                    message="Synthetic payer approval for demo environment."))
                paid = round(approved * rng.uniform(.85, 1.0), 2)
                if rng.random() < .82:
                    s.add(Payment(denial_id=d.id, claim_id=c.id, payment_reference=f"PAY-{i}", amount=paid, status="PAID",
                                  payment_date=datetime.now(timezone.utc)-timedelta(days=rng.randint(0, 30)), verified=True, source="PAYER_SIMULATOR"))
                    d.outcome="COMPLETED"; d.recovered_amount=paid
                    s.add(Event(denial_id=d.id, stage="PAYMENT", status="VERIFIED", message=f"Synthetic payment verified: ₹{paid:,.0f}."))
                else:
                    d.outcome="PAYER_APPROVED"
                    s.add(Event(denial_id=d.id, stage="PAYER_RESPONSE", status="APPROVED", message="Payer approved; payment verification pending."))
            else:
                if d.status == "HUMAN_REVIEW":
                    s.add(Event(denial_id=d.id, stage="HUMAN_REVIEW", status="PENDING", message="Low-confidence synthetic case routed to human review."))
                else:
                    s.add(Event(denial_id=d.id, stage="CLASSIFICATION", status="COMPLETED", message="Synthetic AI classification completed; reviewer gate remains available."))
            # Give every demo case a realistic document trail.
            s.add(Document(denial_id=d.id, name=f"{no}_denial_letter.pdf", document_type="DENIAL_LETTER", status="INDEXED"))
            s.add(Document(denial_id=d.id, name=f"{no}_clinical_notes.pdf", document_type="CLINICAL_NOTES", status="INDEXED"))
            s.add(Document(denial_id=d.id, name=f"{no}_payer_policy.pdf", document_type="PAYER_POLICY", status="INDEXED"))
            if d.status == "HUMAN_REVIEW":
                s.add(ReviewTask(denial_id=d.id, reason="Confidence below automated submission threshold; validate clinical evidence.", status="PENDING"))

        for title,message,kind in [
            ("Appeal for CLM-1001 submitted successfully.","Payer response is being tracked.","good"),
            ("New denial letter uploaded for CLM-1010.","AI analysis is ready.","info"),
            ("CLM-1008 requires human review.","Low confidence requires manual investigation.","warn"),
            ("Payment received for CLM-1011.","₹1,75,000 verified and counted as recovered.","good"),
        ]:
            if not await s.scalar(select(Notification).where(Notification.title==title)):
                s.add(Notification(title=title,message=message,kind=kind))
        await s.commit()
    print("Demo seeded. Login: demo@denialdesk.local / Demo@12345")

asyncio.run(main())
