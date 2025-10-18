from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import random

app = FastAPI(title="Clinical Trials Mock API")


class ClinicalSearchRequest(BaseModel):
    molecule: str
    indications: List[str] = []
    countries: List[str] = []


@app.post("/search")
async def search_trials(request: ClinicalSearchRequest):
    """Mock ClinicalTrials.gov search endpoint."""

    trials_templates = [
        {
            "phase": "Phase 1",
            "status": "Not yet recruiting",
            "sponsor": "Academic Medical Center"
        },
        {
            "phase": "Phase 2",
            "status": "Recruiting",
            "sponsor": "BioTech Innovations Inc."
        },
        {
            "phase": "Phase 2",
            "status": "Active, not recruiting",
            "sponsor": "Global Pharma Corp"
        },
        {
            "phase": "Phase 3",
            "status": "Recruiting",
            "sponsor": "Major Pharma Ltd"
        },
        {
            "phase": "Phase 3",
            "status": "Completed",
            "sponsor": "Research University Hospital"
        }
    ]

    trials = []
    num_trials = random.randint(2, 5)

    for i in range(num_trials):
        template = random.choice(trials_templates)
        indication = random.choice(request.indications) if request.indications else "General condition"
        country = random.choice(request.countries) if request.countries else "US"

        trial = {
            "id": f"NCT{random.randint(10000000, 99999999)}",
            "title": f"Study of {request.molecule} in {indication}",
            "phase": template["phase"],
            "status": template["status"],
            "country": country,
            "sponsor": template["sponsor"],
            "results_summary": f"Preliminary results show promise in treating {indication}",
            "url": f"https://clinicaltrials.gov/ct2/show/NCT{random.randint(10000000, 99999999)}"
        }
        trials.append(trial)

    phase_3_count = sum(1 for t in trials if t["phase"] == "Phase 3")
    completed_count = sum(1 for t in trials if t["status"] == "Completed")

    clinical_signal_score = min(
        0.3 + (phase_3_count * 0.2) + (completed_count * 0.15),
        0.95
    )

    return {
        "trials": trials,
        "clinical_signal_score": round(clinical_signal_score, 2)
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "clinical_trials_mock"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
