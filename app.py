from pathlib import Path
from starlette.concurrency import run_in_threadpool
import traceback

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Atlas AI",
    description=(
        "LangGraph Multi-Agent Travel Planner with Supervisor, Guardrails, "
        "Human-in-the-Loop, and FastAPI Frontend"
    ),
    version="2.0.0",
)

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _backend_helpers():
    """Load the graph only when an API request needs it."""
    from backend import resume_travel_agent, run_travel_agent

    return run_travel_agent, resume_travel_agent


class TravelRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ApprovalRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    approved: bool
    feedback: str = ""


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


@app.post("/api/travel")
async def travel_planner(request_data: TravelRequest):
    try:
        run_travel_agent, _ = _backend_helpers()
        user_message = request_data.message.strip()

        if not user_message:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Message cannot be empty.",
                },
            )

        result = await run_in_threadpool(
            run_travel_agent,
            user_input=user_message,
            thread_id=request_data.thread_id,
        )

        return JSONResponse(
            content={
                "success": True,
                **result,
            }
        )

    except Exception as exc:
        print("ERROR:", exc)
        traceback.print_exc()

        provider_status = getattr(exc, "status_code", None)
        status_code = 429 if provider_status == 429 else 502 if provider_status == 401 else 500
        error_message = (
            "The AI provider is temporarily rate-limited. Please wait a moment "
            "and try again."
            if status_code == 429
            else "The AI provider rejected the API key. Check GROQ_API_KEY in Vercel."
            if status_code == 502
            else str(exc)
        )

        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": error_message,
            },
        )


@app.post("/api/travel/approve")
async def approve_travel_plan(request_data: ApprovalRequest):
    try:
        _, resume_travel_agent = _backend_helpers()
        if not request_data.approved and not request_data.feedback.strip():
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Please provide revision feedback when rejecting the draft.",
                },
            )

        result = await run_in_threadpool(
            resume_travel_agent,
            thread_id=request_data.thread_id,
            approved=request_data.approved,
            feedback=request_data.feedback,
        )

        return JSONResponse(
            content={
                "success": True,
                **result,
            }
        )

    except Exception as exc:
        print("APPROVAL ERROR:", exc)
        traceback.print_exc()

        provider_status = getattr(exc, "status_code", None)
        status_code = 429 if provider_status == 429 else 502 if provider_status == 401 else 500
        error_message = (
            "The AI provider is temporarily rate-limited. Please wait a moment "
            "and try again."
            if status_code == 429
            else "The AI provider rejected the API key. Check GROQ_API_KEY in Vercel."
            if status_code == 502
            else str(exc)
        )

        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": error_message,
            },
        )


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "message": "Atlas AI API is running",
        "features": [
            "supervisor_agent",
            "input_guardrail",
            "human_in_the_loop",
        ],
    }


@app.get("/favicon.ico")
async def favicon():
    return JSONResponse(content={})


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
