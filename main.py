"""FastAPI 앱 — Telegram Webhook 처리"""
import asyncio
import json
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from config import TELEGRAM_API, ALLOWED_CHAT_ID
from claude_client import analyze_workout
from notion_client import get_recent_records, add_or_update_workout

# ── media group 버퍼 ──────────────────────────────────────────────────────────
# 같은 media_group_id의 메시지를 모아서 일괄 처리
_media_groups: dict[str, dict] = {}
_media_timers: dict[str, asyncio.Task] = {}
_lock = asyncio.Lock()

# ── Telegram 헬퍼 ─────────────────────────────────────────────────────────────

async def send_message(chat_id: int, text: str) -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(f"{TELEGRAM_API}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        })

async def send_typing(chat_id: int) -> None:
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(f"{TELEGRAM_API}/sendChatAction", json={
            "chat_id": chat_id, "action": "typing"
        })

# ── 운동 기록 처리 코어 ───────────────────────────────────────────────────────

async def process_workout(chat_id: int, file_ids: list[str], memo: str) -> None:
    """이미지 분석 → Notion 저장 → 텔레그램 피드백 전송"""
    await send_typing(chat_id)

    try:
        # 1. 최근 기록 조회 (Claude 컨텍스트용)
        recent = await get_recent_records(n=5)

        # 2. Claude API 호출
        await send_typing(chat_id)
        data = await analyze_workout(file_ids, memo, recent)
        print(f"[Claude] 파싱 완료: {json.dumps(data, ensure_ascii=False)}")

        # 3. Notion 저장
        await add_or_update_workout(data)

        # 4. 피드백 전송
        feedback = data.get("feedback", "피드백 생성 실패")
        date     = data.get("date", "")
        etype    = data.get("exercise_type", "")
        duration = data.get("duration", "")
        kcal     = data.get("calories", "")
        weight   = data.get("weight", "-")

        summary = f"📅 {date}  🏋️ {etype} {duration}"
        if kcal: summary += f"  🔥 {kcal}kcal"
        if weight and weight != "-": summary += f"  ⚖️ {weight}"

        await send_message(chat_id, f"{summary}\n\n{feedback}")

    except json.JSONDecodeError as e:
        print(f"[오류] Claude JSON 파싱 실패: {e}")
        await send_message(chat_id, "😥 이미지 분석 중 오류가 났어! 운동 요약 화면이 맞는지 확인해줄래? 🙏")
    except Exception as e:
        print(f"[오류] {type(e).__name__}: {e}")
        await send_message(chat_id, f"😥 앗, 뭔가 문제가 생겼어!\n\n오류: {e}")

# ── media group 처리 ──────────────────────────────────────────────────────────

async def _flush_media_group(group_id: str, chat_id: int) -> None:
    """3초 대기 후 같은 그룹 이미지 일괄 처리"""
    await asyncio.sleep(3)
    async with _lock:
        group = _media_groups.pop(group_id, {})
        _media_timers.pop(group_id, None)

    if group:
        await process_workout(chat_id, group["file_ids"], group.get("memo", ""))

async def handle_media_group(msg: dict, group_id: str) -> None:
    chat_id = msg["chat"]["id"]
    file_id = msg["photo"][-1]["file_id"]
    caption = msg.get("caption", "")

    async with _lock:
        if group_id not in _media_groups:
            _media_groups[group_id] = {"file_ids": [], "memo": ""}
            task = asyncio.create_task(_flush_media_group(group_id, chat_id))
            _media_timers[group_id] = task

        _media_groups[group_id]["file_ids"].append(file_id)
        if caption:
            _media_groups[group_id]["memo"] += caption

# ── 단일 메시지 처리 ──────────────────────────────────────────────────────────

async def handle_message(msg: dict) -> None:
    chat_id = msg.get("chat", {}).get("id")

    # 허용된 사용자만 처리
    if chat_id != ALLOWED_CHAT_ID:
        print(f"[보안] 허용되지 않은 chat_id: {chat_id}")
        return

    # 사진 메시지
    if "photo" in msg:
        group_id = msg.get("media_group_id")
        if group_id:
            await handle_media_group(msg, group_id)
        else:
            # 단일 이미지
            file_id = msg["photo"][-1]["file_id"]
            memo    = msg.get("caption", "")
            asyncio.create_task(process_workout(chat_id, [file_id], memo))

    # 텍스트 전용 메시지
    elif "text" in msg:
        text = msg["text"].strip()
        if text == "/start":
            await send_message(
                chat_id,
                "안녕하세요! 💪 운동 후 애플 피트니스 스크린샷을 보내주시면 기록하고 피드백 드릴게요!\n\n"
                "📸 운동 요약 화면 1장, 또는\n"
                "📸📸 요약 + 심박수 상세 2장을 동시에 보내세요."
            )
        elif text == "/status":
            await send_message(chat_id, "✅ 봇이 정상 작동 중이에요!")
        else:
            await send_message(chat_id, "운동 스크린샷을 보내주세요! 📸")

# ── FastAPI 앱 ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("✅ Workout Bot 시작")
    yield
    print("🛑 Workout Bot 종료")

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def webhook(request: Request) -> Response:
    try:
        update = await request.json()
    except Exception:
        return Response(status_code=400)

    if "message" in update:
        asyncio.create_task(handle_message(update["message"]))

    # Telegram은 200 OK를 빠르게 받아야 재전송을 안 함
    return Response(status_code=200)

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
