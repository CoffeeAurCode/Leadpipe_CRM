from fastapi import FastAPI
from app.routes import complaints
from app.routes import voice

app = FastAPI(title="AI Complaint System")

app.include_router(complaints.router)
app.include_router(voice.router)


@app.get("/")
async def root():
    return {"status": "Backend running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
