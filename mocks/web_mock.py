from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import random

app = FastAPI(title="Web Intelligence Mock API")


class WebSearchRequest(BaseModel):
    molecule: str
    indications: List[str] = []


@app.post("/search")
async def search_web_intel(request: WebSearchRequest):
    """Mock web intelligence aggregation endpoint."""

    journals = [
        "The Lancet",
        "New England Journal of Medicine",
        "JAMA",
        "Nature Medicine",
        "Science Translational Medicine",
        "Cell",
        "BMJ"
    ]

    authors_pool = [
        ["Smith J", "Johnson A", "Williams B"],
        ["Brown C", "Davis M", "Garcia R"],
        ["Miller T", "Wilson K", "Moore P"],
        ["Taylor E", "Anderson L", "Thomas H"],
        ["Jackson M", "White D", "Harris N"]
    ]

    publications = []
    for i in range(random.randint(3, 8)):
        indication = random.choice(request.indications) if request.indications else "disease"
        pub = {
            "title": f"Efficacy of {request.molecule} in treating {indication}: A randomized controlled trial",
            "authors": random.choice(authors_pool),
            "journal": random.choice(journals),
            "year": random.randint(2018, 2024),
            "doi": f"10.{random.randint(1000, 9999)}/{random.randint(100000, 999999)}",
            "url": f"https://doi.org/10.{random.randint(1000, 9999)}/{random.randint(100000, 999999)}",
            "summary": f"This study demonstrates the potential of {request.molecule} in clinical applications for {indication}."
        }
        publications.append(pub)

    guidelines = [
        {
            "title": f"Clinical practice guidelines for {request.molecule} use",
            "organization": "WHO",
            "year": 2023,
            "url": "https://www.who.int/publications/guidelines",
            "relevance": "high"
        },
        {
            "title": f"Treatment protocols involving {request.molecule}",
            "organization": "National Institute of Health",
            "year": 2024,
            "url": "https://www.nih.gov/health-information",
            "relevance": "medium"
        }
    ]

    news = [
        {
            "title": f"Breakthrough study: {request.molecule} shows promise in new indication",
            "source": "Medical News Today",
            "date": "2024-09-15",
            "url": "https://www.medicalnewstoday.com/articles/breakthrough-study",
            "sentiment": "positive"
        },
        {
            "title": f"FDA approves expanded use of {request.molecule}",
            "source": "Reuters Health",
            "date": "2024-08-22",
            "url": "https://www.reuters.com/health/fda-approval",
            "sentiment": "positive"
        }
    ]

    return {
        "publications": publications,
        "guidelines": guidelines,
        "news": news
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "web_intel_mock"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
