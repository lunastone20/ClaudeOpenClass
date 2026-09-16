import random

from fastapi import FastAPI, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="number-game-secret-key")

templates = Jinja2Templates(directory="templates")

MIN_NUM = 1
MAX_NUM = 100


def start_new_game(session: dict) -> None:
    session["answer"] = random.randint(MIN_NUM, MAX_NUM)
    session["tries"] = 0
    session["message"] = "숫자를 하나 골라서 입력해보세요!"
    session["status"] = "start"
    session["done"] = False
    session["low"] = MIN_NUM
    session["high"] = MAX_NUM
    session["history"] = []


def render(request: Request):
    session = request.session
    span = MAX_NUM - MIN_NUM + 1
    low = session["low"]
    high = session["high"]

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "message": session["message"],
            "tries": session["tries"],
            "done": session["done"],
            "status": session["status"],
            "low": low,
            "high": high,
            "fill_left": round((low - MIN_NUM) / span * 100, 2),
            "fill_width": round((high - low + 1) / span * 100, 2),
            "history": list(reversed(session["history"]))[:8],
            "min_num": MIN_NUM,
            "max_num": MAX_NUM,
        },
    )


SESSION_KEYS = {"answer", "tries", "message", "status", "done", "low", "high", "history"}


@app.get("/")
def index(request: Request):
    if not SESSION_KEYS.issubset(request.session):
        start_new_game(request.session)
    return render(request)


@app.post("/guess")
def guess(request: Request, guess: str = Form(...)):
    session = request.session
    if not SESSION_KEYS.issubset(session):
        start_new_game(session)

    if session["done"]:
        return RedirectResponse("/", status_code=303)

    if not guess.isdigit() or not (MIN_NUM <= int(guess) <= MAX_NUM):
        session["status"] = "invalid"
        session["message"] = f"{MIN_NUM}~{MAX_NUM} 사이의 숫자만 입력해주세요."
        return RedirectResponse("/", status_code=303)

    value = int(guess)
    answer = session["answer"]
    session["tries"] += 1

    if value < answer:
        session["low"] = max(session["low"], value + 1)
        session["status"] = "low"
        session["message"] = "더 높은 숫자입니다! ⬆️"
        session["history"].append({"value": value, "result": "low"})
    elif value > answer:
        session["high"] = min(session["high"], value - 1)
        session["status"] = "high"
        session["message"] = "더 낮은 숫자입니다! ⬇️"
        session["history"].append({"value": value, "result": "high"})
    else:
        tries = session["tries"]
        session["status"] = "correct"
        session["message"] = f"정답입니다! {tries}번 만에 맞추셨습니다. 축하합니다! 🎉"
        session["history"].append({"value": value, "result": "correct"})
        session["done"] = True

    return RedirectResponse("/", status_code=303)


@app.post("/new")
def new_game(request: Request):
    start_new_game(request.session)
    return RedirectResponse("/", status_code=303)
