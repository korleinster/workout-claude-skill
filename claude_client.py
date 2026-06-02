"""Claude API 클라이언트 — 운동 이미지 분석 및 피드백 생성"""
import base64
import json
import re
import httpx
import anthropic
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, SYSTEM_PROMPT, TELEGRAM_FILE_API

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# ── 이미지 다운로드 ───────────────────────────────────────────────────────────

async def download_telegram_image(file_path: str) -> tuple[bytes, str]:
    """Telegram file_path → (이미지 바이트, media_type)"""
    url = f"{TELEGRAM_FILE_API}/{file_path}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(url)
        r.raise_for_status()
        media_type = "image/png" if file_path.lower().endswith(".png") else "image/jpeg"
        return r.content, media_type

async def get_telegram_file_path(file_id: str) -> str:
    """file_id → file_path"""
    from config import TELEGRAM_API
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{TELEGRAM_API}/getFile", params={"file_id": file_id})
        r.raise_for_status()
        return r.json()["result"]["file_path"]

# ── Claude API 호출 ───────────────────────────────────────────────────────────

async def analyze_workout(
    file_ids: list[str],
    memo: str,
    recent_records: str,
) -> dict:
    """
    Telegram file_id 목록 + 메모 + 최근 기록 → 파싱된 운동 데이터 dict
    """
    content: list[dict] = []

    # 이미지 다운로드 및 base64 인코딩
    for file_id in file_ids:
        file_path = await get_telegram_file_path(file_id)
        img_bytes, media_type = await download_telegram_image(file_path)
        b64 = base64.standard_b64encode(img_bytes).decode()
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": b64},
        })

    # 텍스트 컨텍스트
    text_parts = []
    if recent_records:
        text_parts.append(f"현재까지의 운동 기록 (최신순):\n{recent_records}")
    if memo:
        text_parts.append(f"메모: {memo}")
    text_parts.append("위 이미지를 분석해서 JSON만 반환해주세요.")
    content.append({"type": "text", "text": "\n\n".join(text_parts)})

    response = _client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )

    raw = response.content[0].text.strip()

    # ```json ... ``` 블록 추출
    m = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
    if m:
        raw = m.group(1)

    return json.loads(raw)
