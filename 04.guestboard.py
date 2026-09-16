import hashlib
import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, DictLoader, select_autoescape

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "guestboard.json"

NAME_MAX = 20
MESSAGE_MAX = 500
PASSWORD_MAX = 20

app = FastAPI()


def load_entries() -> list[dict]:
    if not DATA_FILE.exists():
        return []
    with DATA_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def save_entries(entries: list[dict]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def avatar_hue(name: str) -> int:
    return int(hashlib.sha256(name.encode("utf-8")).hexdigest(), 16) % 360


FLASH_MESSAGES = {
    "deleted": ("success", "글이 삭제되었습니다."),
    "wrong_password": ("error", "비밀번호가 일치하지 않습니다."),
    "not_found": ("error", "이미 삭제된 글입니다."),
    "invalid": ("error", "이름과 내용을 모두 입력해주세요."),
}

TEMPLATES = {
    "index.html": """
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>방명록</title>
<style>
    :root {
        --green-50: #f0faf3;
        --green-100: #d9f2e3;
        --green-400: #4caf7d;
        --green-500: #2f9e5e;
        --green-600: #22824c;
        --green-700: #1b6a3e;
        --ink: #1f2a24;
    }
    * { box-sizing: border-box; }
    body {
        margin: 0;
        min-height: 100vh;
        font-family: "Segoe UI", "Apple SD Gothic Neo", sans-serif;
        background: linear-gradient(160deg, var(--green-50) 0%, #e8f6ee 45%, #dff3e8 100%);
        color: var(--ink);
        padding: 48px 16px 80px;
    }
    .wrap {
        max-width: 620px;
        margin: 0 auto;
    }
    header {
        text-align: center;
        margin-bottom: 28px;
    }
    header h1 {
        margin: 0 0 6px;
        font-size: 30px;
        color: var(--green-700);
    }
    header p {
        margin: 0;
        color: #5b6b60;
        font-size: 14px;
    }
    .flash {
        border-radius: 12px;
        padding: 12px 16px;
        font-size: 14px;
        font-weight: 600;
        margin-bottom: 20px;
        text-align: center;
    }
    .flash-success { background: var(--green-100); color: var(--green-700); }
    .flash-error { background: #fde8e8; color: #b23b3b; }

    .write-card {
        background: #ffffff;
        border-radius: 18px;
        padding: 24px;
        box-shadow: 0 10px 30px rgba(31, 100, 60, 0.08);
        margin-bottom: 32px;
        border: 1px solid var(--green-100);
    }
    .write-card h2 {
        margin: 0 0 16px;
        font-size: 16px;
        color: var(--green-700);
    }
    .field { margin-bottom: 12px; }
    .field label {
        display: block;
        font-size: 12px;
        font-weight: 600;
        color: #4a5750;
        margin-bottom: 4px;
    }
    .row-2 {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
    }
    input[type="text"],
    input[type="password"],
    textarea {
        width: 100%;
        padding: 10px 12px;
        border-radius: 10px;
        border: 1.5px solid #d7e8dd;
        font-size: 14px;
        font-family: inherit;
        background: #fbfffc;
        outline: none;
        transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    input:focus, textarea:focus {
        border-color: var(--green-400);
        box-shadow: 0 0 0 3px rgba(76, 175, 125, 0.18);
    }
    textarea {
        min-height: 90px;
        resize: vertical;
    }
    .submit-btn {
        width: 100%;
        margin-top: 4px;
        padding: 12px;
        border: none;
        border-radius: 10px;
        background: linear-gradient(135deg, var(--green-500), var(--green-600));
        color: #fff;
        font-size: 15px;
        font-weight: 700;
        cursor: pointer;
        transition: filter 0.15s ease, transform 0.15s ease;
    }
    .submit-btn:hover { filter: brightness(1.06); }
    .submit-btn:active { transform: scale(0.98); }

    .count {
        text-align: center;
        font-size: 13px;
        color: #4a5750;
        margin-bottom: 16px;
    }
    .count b { color: var(--green-700); }

    .entry {
        background: #ffffff;
        border-radius: 16px;
        padding: 18px 20px;
        margin-bottom: 14px;
        border: 1px solid var(--green-100);
        box-shadow: 0 4px 14px rgba(31, 100, 60, 0.05);
    }
    .entry-head {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
    }
    .avatar {
        width: 36px;
        height: 36px;
        border-radius: 50%;
        flex-shrink: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        font-weight: 700;
        font-size: 15px;
    }
    .entry-meta { flex: 1; min-width: 0; }
    .entry-name {
        font-weight: 700;
        font-size: 14px;
        color: var(--ink);
    }
    .entry-date {
        font-size: 12px;
        color: #8a9990;
    }
    .entry-number {
        font-size: 12px;
        color: #a8b8ae;
        font-weight: 600;
    }
    .entry-message {
        font-size: 14px;
        line-height: 1.55;
        white-space: pre-wrap;
        word-break: break-word;
        color: #2c352f;
        margin-bottom: 10px;
    }
    details.delete-box { font-size: 12px; }
    details.delete-box summary {
        cursor: pointer;
        color: #9cb0a4;
        list-style: none;
        width: fit-content;
    }
    details.delete-box summary::-webkit-details-marker { display: none; }
    details.delete-box summary:hover { color: var(--green-600); }
    .delete-form {
        margin-top: 8px;
        display: flex;
        gap: 6px;
    }
    .delete-form input {
        flex: 1;
        padding: 7px 10px;
        font-size: 13px;
    }
    .delete-form button {
        padding: 7px 12px;
        border: none;
        border-radius: 8px;
        background: #f3f5f4;
        color: #b23b3b;
        font-size: 12px;
        font-weight: 700;
        cursor: pointer;
    }
    .delete-form button:hover { background: #fde8e8; }

    .empty {
        text-align: center;
        color: #8a9990;
        font-size: 14px;
        padding: 40px 0;
    }
</style>
</head>
<body>
    <div class="wrap">
        <header>
            <h1>🌿 방명록</h1>
            <p>다녀가신 흔적을 남겨주세요</p>
        </header>

        {% if flash %}
        <div class="flash flash-{{ flash[0] }}">{{ flash[1] }}</div>
        {% endif %}

        <div class="write-card">
            <h2>✏️ 글 남기기</h2>
            <form action="/write" method="post">
                <div class="row-2">
                    <div class="field">
                        <label>이름</label>
                        <input type="text" name="name" maxlength="{{ name_max }}" placeholder="닉네임" required>
                    </div>
                    <div class="field">
                        <label>비밀번호 (삭제용)</label>
                        <input type="password" name="password" maxlength="{{ password_max }}" placeholder="비밀번호" required>
                    </div>
                </div>
                <div class="field">
                    <label>내용</label>
                    <textarea name="message" maxlength="{{ message_max }}" placeholder="남기고 싶은 말을 적어주세요" required></textarea>
                </div>
                <button type="submit" class="submit-btn">방명록 남기기</button>
            </form>
        </div>

        <div class="count">총 <b>{{ entries|length }}</b>개의 방명록</div>

        {% if entries %}
            {% for e in entries %}
            <div class="entry">
                <div class="entry-head">
                    <div class="avatar" style="background: hsl({{ e.hue }}, 60%, 45%);">{{ e.initial }}</div>
                    <div class="entry-meta">
                        <div class="entry-name">{{ e.name }}</div>
                        <div class="entry-date">{{ e.created_at }}</div>
                    </div>
                    <div class="entry-number">#{{ e.display_no }}</div>
                </div>
                <div class="entry-message">{{ e.message }}</div>
                <details class="delete-box">
                    <summary>삭제</summary>
                    <form class="delete-form" action="/delete/{{ e.id }}" method="post">
                        <input type="password" name="password" placeholder="비밀번호 입력" required>
                        <button type="submit">삭제</button>
                    </form>
                </details>
            </div>
            {% endfor %}
        {% else %}
            <div class="empty">아직 남겨진 방명록이 없어요. 첫 글을 남겨보세요!</div>
        {% endif %}
    </div>
</body>
</html>
""",
}

env = Environment(loader=DictLoader(TEMPLATES), autoescape=select_autoescape())


@app.get("/", response_class=HTMLResponse)
def index(request: Request, msg: str | None = None):
    entries = load_entries()
    view_entries = []
    total = len(entries)
    for idx, e in enumerate(entries):
        view_entries.append(
            {
                "id": e["id"],
                "name": e["name"],
                "message": e["message"],
                "created_at": e["created_at"],
                "hue": avatar_hue(e["name"]),
                "initial": e["name"][:1].upper(),
                "display_no": total - idx,
            }
        )
    view_entries.reverse()

    flash = FLASH_MESSAGES.get(msg) if msg else None
    template = env.get_template("index.html")
    html = template.render(
        entries=view_entries,
        flash=flash,
        name_max=NAME_MAX,
        message_max=MESSAGE_MAX,
        password_max=PASSWORD_MAX,
    )
    return HTMLResponse(html)


@app.post("/write")
def write(
    request: Request,
    name: str = Form(...),
    message: str = Form(...),
    password: str = Form(...),
):
    name = name.strip()[:NAME_MAX]
    message = message.strip()[:MESSAGE_MAX]
    password = password[:PASSWORD_MAX]

    if not name or not message or not password:
        return RedirectResponse("/?msg=invalid", status_code=303)

    entries = load_entries()
    next_id = max((e["id"] for e in entries), default=0) + 1
    client_ip = request.client.host if request.client else "unknown"

    entries.append(
        {
            "id": next_id,
            "name": name,
            "message": message,
            "password_hash": hash_password(password),
            "created_at": datetime.now().strftime("%Y.%m.%d %H:%M"),
            "ip": client_ip,
        }
    )
    save_entries(entries)
    return RedirectResponse("/", status_code=303)


@app.post("/delete/{entry_id}")
def delete(entry_id: int, password: str = Form(...)):
    entries = load_entries()
    target = next((e for e in entries if e["id"] == entry_id), None)

    if target is None:
        return RedirectResponse("/?msg=not_found", status_code=303)

    if target["password_hash"] != hash_password(password):
        return RedirectResponse("/?msg=wrong_password", status_code=303)

    entries = [e for e in entries if e["id"] != entry_id]
    save_entries(entries)
    return RedirectResponse("/?msg=deleted", status_code=303)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
