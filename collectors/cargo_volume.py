"""World Bank 공개 API로 항만 물동량(컨테이너 처리량) 지표 자동 수집.

API 키 불필요, 완전 공개 엔드포인트.
지표: IS.SHP.GOOD.TU (Container port traffic, TEU: 20 foot equivalent units), 연간 데이터.
"""
import requests

from db import get_connection, init_db, upsert_indicator, upsert_observations

WB_BASE = "https://api.worldbank.org/v2"
INDICATOR = "IS.SHP.GOOD.TU"

# 세계 전체 + 주요 해운/물동량 국가
COUNTRIES = {
    "WLD": "World",
    "CHN": "China",
    "USA": "United States",
    "KOR": "Korea, Rep.",
    "SGP": "Singapore",
    "NLD": "Netherlands",
}


def _fetch_country_series(country_code):
    url = f"{WB_BASE}/country/{country_code}/indicator/{INDICATOR}"
    params = {"format": "json", "per_page": 1000}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    payload = resp.json()
    if len(payload) < 2 or payload[1] is None:
        return []
    return [
        (f"{row['date']}-01-01", row["value"])
        for row in payload[1]
        if row.get("value") is not None
    ]


def collect():
    conn = get_connection()
    init_db(conn)

    for code, name in COUNTRIES.items():
        try:
            data = _fetch_country_series(code)
        except Exception as e:
            print(f"[cargo_volume] {code} 수집 실패: {e}")
            continue
        if not data:
            print(f"[cargo_volume] {code}: 데이터 없음")
            continue
        indicator_id = upsert_indicator(
            conn,
            code=f"WB_PORT_TRAFFIC_{code}",
            name=f"Container Port Traffic - {name}",
            category="cargo_volume",
            unit="TEU",
            source="worldbank",
            region=code,
        )
        upsert_observations(conn, indicator_id, data)
        print(f"[cargo_volume] {code}: {len(data)}건 upsert 완료")

    conn.close()


if __name__ == "__main__":
    collect()
