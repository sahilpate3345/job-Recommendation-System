from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import os

# --- Load Pinecone API key ---
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
if not PINECONE_API_KEY:
    raise RuntimeError("❌ PINECONE_API_KEY not found in .env file")

# --- Connect to Pinecone ---
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index("job-recommendation")

# --- Load embedding model ---
model = SentenceTransformer("all-MiniLM-L6-v2")

app = FastAPI()

class Req(BaseModel):
    resume_text: str
    experience_years: int

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/recommend")
def recommend(req: Req):
    try:
        resume_text = req.resume_text.lower()

        # 🚫 Reject non-ITI resumes
        if "iti" not in resume_text:
            raise HTTPException(
                status_code=400,
                detail="This system is for ITI trade matching only."
            )

        # Encode resume
        vec = model.encode([req.resume_text])[0].tolist()

        # Query Pinecone
        res = index.query(
            vector=vec,
            top_k=10,
            include_metadata=True
        )

        results = []

        for m in res["matches"]:
            meta = m["metadata"]

            trade = str(meta.get("trade", "")).lower()
            job_role = meta.get("job_role", "N/A")

            job_min_exp = max(int(meta.get("job_min_experience", 1)), 1)
            exp_match = min(req.experience_years / job_min_exp, 1)

            # 🎯 Boost if resume mentions trade
            trade_boost = 0.15 if trade and trade in resume_text else 0

            final_score = 0.65 * m["score"] + 0.25 * exp_match + trade_boost

            results.append({
                "job_role": job_role,
                "trade": meta.get("trade", "N/A"),
                "final_score": round(final_score, 3)
            })

        return sorted(results, key=lambda x: x["final_score"], reverse=True)[:5]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
