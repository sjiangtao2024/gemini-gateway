from fastapi import FastAPI

from app.auth.middleware import auth_middleware

app = FastAPI()
app.middleware("http")(auth_middleware)


@app.get("/health")
async def health():
    return {"status": "healthy"}
