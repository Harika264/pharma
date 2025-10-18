from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import random
from datetime import datetime, timedelta

app = FastAPI(title="USPTO Patent Search Mock API")


class PatentSearchRequest(BaseModel):
    molecule: str
    indications: List[str] = []


@app.post("/search")
async def search_patents(request: PatentSearchRequest):
    """Mock USPTO patent search endpoint."""

    patents = []
    num_patents = random.randint(5, 15)

    patent_statuses = ["Active", "Pending", "Expired", "Abandoned"]
    applicants = [
        "Pharmaceutical Innovations LLC",
        "BioMed Research Corp",
        "Global Drug Development Inc",
        "Advanced Therapeutics Ltd",
        "MedTech Solutions GmbH"
    ]

    for i in range(num_patents):
        filing_year = random.randint(2010, 2024)
        filing_date = datetime(filing_year, random.randint(1, 12), random.randint(1, 28))

        indication = random.choice(request.indications) if request.indications else "therapeutic use"

        patent = {
            "patent_number": f"US{random.randint(8000000, 11000000)}B{random.randint(1, 2)}",
            "title": f"Method of treating {indication} using {request.molecule}",
            "applicant": random.choice(applicants),
            "filing_date": filing_date.strftime("%Y-%m-%d"),
            "status": random.choice(patent_statuses),
            "claims_summary": f"Claims cover the use of {request.molecule} for treating {indication} with specific dosage regimens",
            "url": f"https://patents.google.com/patent/US{random.randint(8000000, 11000000)}"
        }
        patents.append(patent)

    active_patents = [p for p in patents if p["status"] == "Active"]
    pending_patents = [p for p in patents if p["status"] == "Pending"]

    fto_flags = []
    if len(active_patents) > 5:
        fto_flags.append("High patent density - potential FTO issues")
    if len(pending_patents) > 3:
        fto_flags.append("Multiple pending patents - monitor for grants")

    ip_risk_score = min(
        0.2 + (len(active_patents) * 0.08) + (len(pending_patents) * 0.05),
        0.95
    )

    return {
        "patents": patents,
        "fto_flags": fto_flags,
        "ip_risk_score": round(ip_risk_score, 2)
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "uspto_mock"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
