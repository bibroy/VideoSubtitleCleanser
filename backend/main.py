import uvicorn
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from routers import subtitle_router, processing_router, translation_router

app = FastAPI(
    title="VideoSubtitleCleanser",
    description="An intelligent video subtitle processing system that improves media viewing experience",
    version="1.0.0"
)

# CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

# Templates
templates = Jinja2Templates(directory="templates")

# Root endpoint
@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Include routers
app.include_router(subtitle_router.router, prefix="/api/subtitles", tags=["subtitles"])
app.include_router(processing_router.router, prefix="/api/process", tags=["processing"])
app.include_router(translation_router.router, prefix="/api/translate", tags=["translation"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
