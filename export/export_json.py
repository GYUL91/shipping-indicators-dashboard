"""SQLite DB 내용을 docs/data/all.json 으로 export (정적 대시보드가 fetch해서 사용)."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "collectors"))
from db import get_connection  # noqa: E402

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "data" / "all.json"


def export():
    conn = get_connection()
    indicators = conn.execute(
        "SELECT id, code, name, category, unit, source, region FROM indicators ORDER BY category, code"
    ).fetchall()

    result = []
    for ind_id, code, name, category, unit, source, region in indicators:
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
