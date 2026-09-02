"""국가물류통합정보센터(NLIC, 국토교통부 산하 공공기관) 공개 통계로 운임지수 자동 수집.

무료, 로그인/API키 불필요. 실제 사이트의 검색 폼(frmSrch)이 그대로 서버사이드 HTML을
반환하는 구조라 requests POST + 정규식 파싱으로 수집한다.

수집 지표:
  - SCFI (상하이컨테이너운임지수, 주간) - 출처: 한국관세물류협회(KCLA)
  - CCFI (중국컨테이너운임지수, 주간) - 출처: 한국관세물류협회(KCLA)
  - BDI (발틱운임지수, 일간) - 출처: 한국관세물류협회(KCLA)
  - 국내 해상운임지수(수출/수입, 항로별, 월간, 천원/2TEU) - 출처: 수출입무역통계(관세청)

참고: https://www.nlic.go.kr/nlic/transInPortCt.action (국외), seaDmstcOcn.action (국내)
"""
import re
from datetime import date

import requests

from db import get_connection, init_db, upsert_indicator, upsert_observations

BASE = "https://www.nlic.go.kr/nlic"
CURRENT_YEAR = date.today().year
START_YEAR = 2014

DATE_RE = re.compile(r'class="list_sb_4"[^>]*>([\d-]+)</li>')
VALUE_RE = re.compile(r'class="list_num_01"[^>]*>([\d,.\-]+)</li>')

DOMESTIC_BLOCK_RE = re.compile(
    r'<div>(\d{4}-\d{2})</div>.*?<li class="list_num_etc">(.*?)</li>', re.DOTALL
)
SPAN_RE = re.compile(r'<span>([^<]+)</span>')

DOMESTIC_ROUTES = ["미국 서부", "미국 동부", "EU", "중국", "일본", "베트남"]


def _to_float(raw):
    raw = raw.strip().replace(",", "")
    if not raw or raw == "-":
        return None
    return float(raw)


def _fetch_international(series_code):
    """series_code: 'CFI' (SCFI+CCFI 동시 반환) or 'BDI'"""
    resp = requests.post(
        f"{BASE}/transInPortCt.action",
        data={
            "command": "LIST",
            "S_TRANSIN_SE": series_code,
            "S_YEAR": str(START_YEAR),
            "F_YEAR": str(CURRENT_YEAR),
        },
        timeout=30,
    )
    resp.raise_for_status()
    resp.encoding = "utf-8"
    text = resp.text

    dates = DATE_RE.findall(text)
    values = [_to_float(v) for v in VALUE_RE.findall(text)]
    return dates, values


def _fetch_domestic(direction):
    """direction: 'XPT'(수출) or 'IMP'(수입). 반환: {route: [(date, value), ...]}"""
    resp = requests.post(
        f"{BASE}/seaDmstcOcn.action",
        data={
            "command": "LIST",
            "S_IMXPRT_SE": direction,
            "S_YEAR": str(CURRENT_YEAR),
            "S_MONTH": "01",
        },
        timeout=30,
    )
    resp.raise_for_status()
    resp.encoding = "utf-8"
    text = resp.text

    by_route = {route: [] for route in DOMESTIC_ROUTES}
    for month, span_block in DOMESTIC_BLOCK_RE.findall(text):
        values = SPAN_RE.findall(span_block)
        if len(values) != len(DOMESTIC_ROUTES):
            continue
        for route, raw in zip(DOMESTIC_ROUTES, values):
            v = _to_float(raw)
            if v is not None:
                by_route[route].append((f"{month}-01", v))
    return by_route


def collect():
    conn = get_connection()
    init_db(conn)

    # --- SCFI / CCFI (같은 요청에서 두 시리즈가 순서대로 반환됨) ---
    try:
        dates, values = _fetch_international("CFI")
        n = len(dates)
        scfi_pairs = [(d, v) for d, v in zip(dates, values[:n]) if v is not None]
        ccfi_pairs = [(d, v) for d, v in zip(dates, values[n : 2 * n]) if v is not None]

        scfi_id = upsert_indicator(
            conn, "SCFI", "Shanghai Containerized Freight Index",
            "freight_index", "index", "nlic", "Global",
        )
        upsert_observations(conn, scfi_id, scfi_pairs)
        print(f"[freight_indices] SCFI: {len(scfi_pairs)}건 upsert 완료")

        ccfi_id = upsert_indicator(
            conn, "CCFI", "China Containerized Freight Index",
            "freight_index", "index", "nlic", "Global",
        )
        upsert_observations(conn, ccfi_id, ccfi_pairs)
        print(f"[freight_indices] CCFI: {len(ccfi_pairs)}건 upsert 완료")
    except Exception as e:
        print(f"[freight_indices] SCFI/CCFI 수집 실패: {e}")

    # --- BDI ---
    try:
        dates, values = _fetch_international("BDI")
        bdi_pairs = [(d, v) for d, v in zip(dates, values) if v is not None]
        bdi_id = upsert_indicator(
            conn, "BDI", "Baltic Dry Index", "freight_index", "index", "nlic", "Global",
        )
        upsert_observations(conn, bdi_id, bdi_pairs)
        print(f"[freight_indices] BDI: {len(bdi_pairs)}건 upsert 완료")
    except Exception as e:
        print(f"[freight_indices] BDI 수집 실패: {e}")

    # --- 국내 해상운임지수 (수출/수입 x 항로별) ---
    for direction, label in [("XPT", "수출"), ("IMP", "수입")]:
        try:
            by_route = _fetch_domestic(direction)
        except Exception as e:
            print(f"[freight_indices] 국내 {label} 운임지수 수집 실패: {e}")
            continue
        for route, pairs in by_route.items():
            if not pairs:
                continue
            code = f"KR_{direction}_{route}"
            indicator_id = upsert_indicator(
                conn, code, f"국내 해상운임지수({label}) - {route}",
                "freight_index", "천원/2TEU", "nlic", route,
            )
            upsert_observations(conn, indicator_id, pairs)
            print(f"[freight_indices] {code}: {len(pairs)}건 upsert 완료")

    conn.close()


if __name__ == "__main__":
    collect()
