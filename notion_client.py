"""Notion API 클라이언트 — 월별 운동 테이블 읽기/쓰기"""
import httpx
from datetime import datetime
from config import NOTION_TOKEN, NOTION_API, NOTION_VERSION, WORKOUT_ROOT_ID, WORKOUT_YEAR_ID, TABLE_COLUMNS, KST

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

# ── 기본 Notion API 헬퍼 ──────────────────────────────────────────────────────

async def _get_blocks(page_id: str) -> list:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{NOTION_API}/blocks/{page_id}/children", headers=HEADERS)
        r.raise_for_status()
        return r.json().get("results", [])

async def _append_blocks(parent_id: str, children: list, after: str | None = None) -> dict:
    body: dict = {"children": children}
    if after:
        body["after"] = after
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.patch(
            f"{NOTION_API}/blocks/{parent_id}/children",
            headers=HEADERS, json=body
        )
        r.raise_for_status()
        return r.json()

async def _update_block(block_id: str, block_type: str, data: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.patch(
            f"{NOTION_API}/blocks/{block_id}",
            headers=HEADERS, json={block_type: data}
        )
        r.raise_for_status()
        return r.json()

async def _create_page(parent_id: str, title: str, children: list | None = None) -> dict:
    body = {
        "parent": {"page_id": parent_id},
        "properties": {"title": {"title": [{"text": {"content": title}}]}},
    }
    if children:
        body["children"] = children
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(f"{NOTION_API}/pages", headers=HEADERS, json=body)
        r.raise_for_status()
        return r.json()

# ── 셀 빌더 ───────────────────────────────────────────────────────────────────

def _cell(text: str | int | None) -> list:
    """rich_text 셀 한 칸"""
    return [{"type": "text", "text": {"content": str(text) if text is not None else ""}}]

def _get_cell_text(cells: list, idx: int) -> str:
    if idx >= len(cells) or not cells[idx]:
        return ""
    rt = cells[idx]
    return "".join(
        (c.get("plain_text") or c.get("text", {}).get("content", ""))
        for c in rt
    )

def _build_row_cells(data: dict, col_count: int) -> list:
    """테이블 컬럼 수에 맞게 cells 배열 생성"""
    avg_bpm  = data.get("avg_bpm", "")
    max_bpm  = data.get("max_bpm", "")
    calories = data.get("calories", "")

    if col_count >= 11:
        # 11컬럼 (심박존 분포 포함)
        return [
            _cell(data.get("date", "")),
            _cell(data.get("exercise_type", "")),
            _cell(data.get("duration", "")),
            _cell(data.get("intensity", "")),
            _cell(avg_bpm),
            _cell(max_bpm),
            _cell(calories),
            _cell(data.get("weight", "-")),
            _cell(data.get("heart_rate_zones", "")),
            _cell(data.get("memo", "")),
            _cell(data.get("feedback", "")),
        ]
    else:
        # 10컬럼 (기존 테이블) — 심박존을 메모에 병합
        hr_zones = data.get("heart_rate_zones", "")
        memo     = data.get("memo", "")
        combined = f"{hr_zones}\n{memo}".strip() if hr_zones and memo else (hr_zones or memo)
        return [
            _cell(data.get("date", "")),
            _cell(data.get("exercise_type", "")),
            _cell(data.get("duration", "")),
            _cell(data.get("intensity", "")),
            _cell(avg_bpm),
            _cell(max_bpm),
            _cell(calories),
            _cell(data.get("weight", "-")),
            _cell(combined),
            _cell(data.get("feedback", "")),
        ]

# ── 월 페이지·테이블 탐색/생성 ───────────────────────────────────────────────

def _now_kst() -> datetime:
    return datetime.now(KST)

def _year_key(dt: datetime) -> str:
    return f"{dt.year}년"

def _month_key(dt: datetime) -> str:
    return f"{dt.year}년_{dt.month:02d}"

def _initial_table_block() -> dict:
    """11컬럼 헤더 포함 초기 테이블 블록"""
    header_cells = [_cell(col) for col in TABLE_COLUMNS]
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": len(TABLE_COLUMNS),
            "has_column_header": True,
            "has_row_header": False,
        },
    }

async def _get_child_pages(page_id: str) -> list[dict]:
    blocks = await _get_blocks(page_id)
    return [
        {"id": b["id"], "title": b["child_page"]["title"]}
        for b in blocks if b.get("type") == "child_page"
    ]

async def _find_or_create_month_page(year_page_id: str, month_key: str) -> str:
    pages = await _get_child_pages(year_page_id)
    page = next((p for p in pages if p["title"] == month_key), None)
    if page:
        return page["id"]

    # 새 월 페이지 생성
    result = await _create_page(year_page_id, month_key)
    return result["id"]

async def _get_or_create_table(month_page_id: str) -> str:
    """테이블 block_id 반환 (없으면 생성)"""
    blocks = await _get_blocks(month_page_id)
    table_block = next((b for b in blocks if b["type"] == "table"), None)
    if table_block:
        return table_block["id"]

    # 테이블 생성
    res = await _append_blocks(month_page_id, [_initial_table_block()])
    table_id = res["results"][0]["id"]

    # 헤더 행 추가
    header_cells = [_cell(col) for col in TABLE_COLUMNS]
    await _append_blocks(table_id, [{
        "object": "block",
        "type": "table_row",
        "table_row": {"cells": header_cells},
    }])
    return table_id

async def get_table_info() -> tuple[str, str]:
    """(month_page_id, table_id) 반환"""
    now  = _now_kst()
    ykey = _year_key(now)
    mkey = _month_key(now)

    # 연도 페이지
    year_pages = await _get_child_pages(WORKOUT_ROOT_ID)
    year_page  = next((p for p in year_pages if p["title"] == ykey), None)
    if not year_page:
        raise RuntimeError(f"연도 페이지 없음: {ykey}. Notion에서 직접 생성해주세요.")
    year_page_id = year_page["id"]

    # 월 페이지
    month_page_id = await _find_or_create_month_page(year_page_id, mkey)

    # 테이블
    table_id = await _get_or_create_table(month_page_id)

    return month_page_id, table_id

# ── 운동 기록 읽기 / 쓰기 ─────────────────────────────────────────────────────

async def get_recent_records(n: int = 5) -> str:
    """최근 n개 운동 기록을 텍스트로 반환 (Claude 프롬프트용)"""
    try:
        _, table_id = await get_table_info()
        rows = await _get_blocks(table_id)
        data_rows = rows[1:]  # 헤더 제외
        recent = data_rows[-n:][::-1]  # 최신순

        lines = []
        for row in recent:
            cells = row["table_row"]["cells"]
            g = lambda i: _get_cell_text(cells, i)
            parts = [f"{g(0)}: {g(1)} {g(2)}, {g(3)}"]
            if g(4): parts.append(f"평균BPM {g(4)}")
            if g(5): parts.append(f"최고BPM {g(5)}")
            if g(6): parts.append(f"{g(6)}kcal")
            if g(7) and g(7) != "-": parts.append(g(7))
            lines.append("- " + ", ".join(parts))

        return "\n".join(lines)
    except Exception as e:
        print(f"[Notion] 최근 기록 조회 실패: {e}")
        return ""

async def add_or_update_workout(data: dict) -> None:
    """운동 기록을 Notion 테이블에 추가 또는 기존 날짜 업데이트"""
    _, table_id = await get_table_info()
    rows = await _get_blocks(table_id)

    header    = rows[0] if rows else None
    data_rows = rows[1:] if rows else []
    col_count = len(header["table_row"]["cells"]) if header else 10

    target_date = data.get("date", "")

    # 중복 날짜 검사 → 있으면 업데이트
    for row in data_rows:
        cells     = row["table_row"]["cells"]
        row_date  = _get_cell_text(cells, 0)
        if row_date == target_date:
            print(f"[Notion] 기존 날짜 업데이트: {target_date}")
            await _update_block(
                row["id"], "table_row",
                {"cells": _build_row_cells(data, col_count)}
            )
            return

    # 새 행 추가
    print(f"[Notion] 새 행 추가: {target_date}")
    await _append_blocks(table_id, [{
        "object": "block",
        "type": "table_row",
        "table_row": {"cells": _build_row_cells(data, col_count)},
    }])
