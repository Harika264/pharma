from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
import random

app = FastAPI(title="EXIM Trade Data Mock API")


class EXIMSearchRequest(BaseModel):
    molecule: str
    countries: List[str] = []


@app.post("/search")
async def search_trade_data(request: EXIMSearchRequest):
    """Mock EXIM trade intelligence endpoint."""

    import_dependency_pct = random.uniform(10, 80)

    source_countries = ["China", "India", "Germany", "USA", "Switzerland", "Ireland", "Japan"]
    top_sources = []

    for i in range(random.randint(3, 5)):
        country = random.choice([c for c in source_countries if c not in [s["country"] for s in top_sources]])
        top_sources.append({
            "country": country,
            "percentage": round(random.uniform(10, 40), 2),
            "volume_kg": random.randint(10000, 500000)
        })

    trend_timeseries = []
    for year in range(2020, 2025):
        for quarter in ["Q1", "Q2", "Q3", "Q4"]:
            trend_timeseries.append({
                "period": f"{year}-{quarter}",
                "import_volume_kg": random.randint(50000, 300000),
                "export_volume_kg": random.randint(20000, 150000),
                "net_import_dependency": round(random.uniform(15, 70), 2)
            })

    trade_data = {
        "import_dependency_pct": round(import_dependency_pct, 2),
        "top_sources": top_sources,
        "trend_timeseries": trend_timeseries[-8:]
    }

    return {
        "trade": trade_data
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "exim_mock"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
