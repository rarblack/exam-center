
import json
import random
from typing import Any
import uuid
import time
from fastapi import FastAPI, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from questions.cert_17_questions import QUESTIONS as CERT_17_QUESTIONS
from questions.cert_18_questions import QUESTIONS as CERT_18_QUESTIONS

app = FastAPI()
templates = Jinja2Templates(directory="src/templates")

QUESTION_POOL = CERT_17_QUESTIONS

exam_sessions: dict[str, Any] = {}

@app.get("/", response_class=HTMLResponse)
async def quiz_page(request: Request):
    return templates.TemplateResponse("quiz.html", {
        "request": request,
        "questions": QUESTION_POOL
    })

@app.get("/certifications/{version}", response_class=HTMLResponse)
async def demo_certification_page(version: int, request: Request):
    return templates.TemplateResponse("certification.html", {
        "request": request,
        "version": version
        })

@app.post("/start-session")
async def start_session(payload: dict = Body(...)):
    question_count = min(int(payload.get("question_count", 100)), len(QUESTION_POOL))
    duration_minutes = max(1, int(payload.get("duration_minutes", 90)))

    certification_version = payload.get("certification_version")

    questions = None
    if certification_version == 17:
        questions = sorted(random.sample(CERT_17_QUESTIONS, question_count), key=lambda x: x["id"])
    elif certification_version == 18:
        questions = random.sample(CERT_18_QUESTIONS, question_count)
    else:
        questions = random.sample(QUESTION_POOL, question_count)

    session_id = str(uuid.uuid4())

    exam_sessions[session_id] = {
        "questions": questions,
        "start_time": time.time(),
        "duration": duration_minutes * 60,
        "answers": {}
    }

    return {"session_id": session_id, "duration": duration_minutes * 60}

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    return exam_sessions.get(session_id, {})

@app.post("/answer/{session_id}/{question_id}")
async def save_answer(session_id: str, question_id: str, payload: dict):
    session = exam_sessions.get(session_id)

    if session:
        session["answers"][question_id] = payload["choice_index"]
    return {"status": "saved"}

@app.post("/submit/{session_id}")
async def submit_exam(session_id: str):
    session = exam_sessions.get(session_id)

    if not session:
        return JSONResponse({"error": "Invalid session"}, status_code=400)

    if session:
        questions = session["questions"]
        answers = session["answers"]

        score: float = 0.0
        correct = 0
        wrong = 0
        details = []

        for q in questions:
            qid = str(q["id"])
            correct_index = next((i for i, c in enumerate(q["choices"]) if c["answer"]), None)
            selected = answers.get(qid)
            is_correct = selected == correct_index if selected is not None else False

            if selected is not None:
                if is_correct:
                    score += 1
                    correct += 1
                else:
                    score -= 0.5
                    wrong += 1

            details.append({
                "question_id": qid,
                "correct_index": correct_index,
                "selected_index": selected,
                "is_correct": is_correct
            })

        total = len(questions)
        percentage = round((score / total) * 100, 2)
        passed = percentage >= 70

        report = {
            "total_questions": total,
            "correct": correct,
            "wrong": wrong,
            "score": score,
            "percentage": percentage,
            "passed": passed,
            "details": details,
            "timestamp": time.time()
        }

        with open(f"reports/report_{session_id}.json", "w") as file:
            json.dump(report, file, indent=4)

        return report
