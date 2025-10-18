from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import random

app = FastAPI(title="IQVIA Market Insights Mock API")


class IQVIASearchRequest(BaseModel):
    molecule: str
    indications: List[str] = []
    countries: List[str] = []


@app.post("/search")
async def search_market_data(request: IQVIASearchRequest):
    """Mock IQVIA market intelligence endpoint."""

    market_size = random.uniform(100, 5000)
    cagr = random.uniform(3, 15)

    competitors = [
        "Pfizer Inc.",
        "Novartis AG",
        "Roche Holding AG",
        "Johnson & Johnson",
        "Merck & Co.",
        "AstraZeneca PLC",
        "Bristol-Myers Squibb",
        "GSK plc"
    ]

    selected_competitors = random.sample(competitors, random.randint(3, 6))

    market_trends = ["Growing", "Stable", "Declining"]
    trend = random.choice(market_trends)

    market_data = {
        "market_size_usd": round(market_size, 2),
        "cagr": round(cagr, 2),
        "competitors": selected_competitors,
        "market_trend": trend
    }

    unmet_gap_score = random.uniform(0.4, 0.9)

    if trend == "Growing" and cagr > 8:
        unmet_gap_score = min(unmet_gap_score + 0.1, 0.95)

    return {
        "market": market_data,
        "unmet_gap_score": round(unmet_gap_score, 2)
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "iqvia_mock"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
