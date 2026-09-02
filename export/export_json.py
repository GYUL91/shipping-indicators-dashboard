"""SQLite DB 내용을 docs/data/all.json 으로 export (정적 대시보드가 fetch해서 사용).

지표별로 최신값/역대 최고·최저/전년동기대비 변화율 등 기초 통계(stats)도 함께 계산해서
대시보드의 인사이트 패널이 정적 파일만으로 그릴 수 있게 한다.
"""
import json
import sys
from datetime import date as date_cls, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "collectors"))
from db import get_connection  # noqa: E402

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "data" / "all.json"


def _compute_stats(obs):
    """obs: [(date_str, value), ...] 오름차순. 최신/최고/최저/YoY 변화율 계산."""
    if not obs:
        return None

    latest_date, latest_value = obs[-1]
    max_row = max(obs, key=lambda r: r[1])
    min_row = min(obs, key=lambda r: r[1])

    yoy = None
    try:
        latest_d = date_cls.fromisoformat(latest_date)
        cutoff = latest_d - timedelta(days=365)
        prior = [(d, v) for d, v in obs if date_cls.fromisoformat(d) <= cutoff]
        if prior:
            prior_value = prior[-1][1]
            if prior_value:
                yoy = round((latest_value - prior_value) / prior_value * 100, 1)
    except ValueError:
        pass

    return {
        "latest_date": latest_date,
        "latest_value": latest_value,
        "max_date": max_row[0],
        "max_value": max_row[1],
        "min_date": min_row[0],
        "min_value": min_row[1],
        "yoy_change_pct": yoy,
    }


def export():
    conn = get_connection()
    indicators = conn.execute(
        "SELECT id, code, name, category, unit, source, region, source_url FROM indicators ORDER BY category, code"
    ).fetchall()

    result = []
    for ind_id, code, name, category, unit, source, region, source_url in indicators:
        obs = conn.execute(
            "SELECT date, value FROM observations WHERE indicator_id = ? ORDER BY date",
            (ind_id,),
        ).fetchall()
        result.append(
            {
                "code": code,
                "name": name,
                "category": category,
                "unit": unit,
                "source": source,
                "region": region,
                "source_url": source_url,
                "stats": _compute_stats(obs),
                "observations": [{"date": d, "value": v} for d, v in obs],
            }
        )
    conn.close()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "indicators": result,
    }
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[export_json] {len(result)}개 지표 -> {OUTPUT_PATH}")


if __name__ == "__main__":
    export()
