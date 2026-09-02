"""EIA(미국 에너지정보청) 공개 API로 유가/연료비 지표 자동 수집.

무료 API 키가 필요합니다: https://www.eia.gov/opendata/register.php
환경변수 EIA_API_KEY 가 없으면 조용히 스킵합니다 (파이프라인 전체를 막지 않기 위함).

수집 지표:
  - EIA_BRENT: Europe Brent Spot Price FOB (달러/배럴, 일간) - 해운 연료비와 강하게 연동되는 국제 유가 벤치마크
  - EIA_WTI: WTI Spot Price FOB (달러/배럴, 일간)
  - EIA_DIESEL_US: 미국 디젤 소매가 (달러/갤런, 주간) - 벙커유 대체 프록시
"""
import os
import requests

from db import get_connection, init_db, upsert_indicator, upsert_observations

EIA_BASE = "https://api.eia.gov/v2"

SPOT_PRICE_SERIES = [
    {
        "code": "EIA_BRENT",
        "name": "Europe Brent Spot Price FOB",
        "series_id": "RBRTE",
        "unit": "USD/barrel",
        "path": "petroleum/pri/spt",
    },
    {
        "code": "EIA_WTI",
        "name": "Cushing OK WTI Spot Price FOB",
        "series_id": "RWTC",
        "unit": "USD/barrel",
        "path": "petroleum/pri/spt",
    },
]

DIESEL_SERIES = {
    "code": "EIA_DIESEL_US",
    "name": "U.S. No 2 Diesel Retail Prices",
    "series_id": "EMD_EPD2D_PTE_NUS_DPG",
    "unit": "USD/gallon",
    "path": "petroleum/pri/gnd",
}


def _fetch_series(api_key, path, series_id, page_size=5000, max_pages=20):
    """EIA API v2는 한 번에 최대 5000행만 반환하므로 offset을 이동하며 전체 이력을
    끝까지(가장 오래된 데이터까지) 페이지네이션으로 수집한다."""
    url = f"{EIA_BASE}/{path}/data/"
    all_rows = []
    for page in range(max_pages):
        params = {
            "api_key": api_key,
            "facets[series][]": series_id,
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "offset": page * page_size,
            "length": page_size,
        }
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        rows = resp.json()["response"]["data"]
        if not rows:
            break
        all_rows.extend(rows)
        if len(rows) < page_size:
            break
    return [(row["period"], row["value"]) for row in all_rows if row.get("value") is not None]


def collect():
    api_key = os.environ.get("EIA_API_KEY")
    if not api_key:
        print("[fuel_prices] EIA_API_KEY 미설정 — 유가 지표 수집을 건너뜁니다.")
        return

    conn = get_connection()
    init_db(conn)

    for series in SPOT_PRICE_SERIES + [DIESEL_SERIES]:
        try:
            data = _fetch_series(api_key, series["path"], series["series_id"])
        except Exception as e:
            print(f"[fuel_prices] {series['code']} 수집 실패: {e}")
            continue
        indicator_id = upsert_indicator(
            conn,
            code=series["code"],
            name=series["name"],
            category="fuel_price",
            unit=series["unit"],
            source="eia",
            region="US" if "US" in series["code"] else "Global",
        )
        upsert_observations(conn, indicator_id, data)
        print(f"[fuel_prices] {series['code']}: {len(data)}건 upsert 완료")

    conn.close()


if __name__ == "__main__":
    collect()
