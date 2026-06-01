from fastapi import FastAPI

app = FastAPI(
    title="MenuScan API",
    description="API số hóa menu nhà hàng",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)


@app.get("/")
def root():
    return {"message": "MenuScan API is running!"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
