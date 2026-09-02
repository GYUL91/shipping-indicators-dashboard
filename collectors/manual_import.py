"""수동 입력 CSV(BDI/SCFI/CCFI, 선대 통계 등 유료·비API 지표)를 DB에 반영.

manual_data/ 폴더 안의 *.csv 파일을 모두 읽어들인다.
CSV 컬럼: indicator_code,indicator_name,category,unit,region,date,value
"""
import csv
import sys
from pathlib import Path

from db import get_connection, init_db, upsert_indicator, upsert_observations

MANUAL_DATA_DIR = Path(__file__).resolve().parent.parent / "manual_data"


def _load_csv(path):
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def collect():
    conn = get_connection()
    init_db(conn)

    csv_files = sorted(MANUAL_DATA_DIR.glob("*.csv"))
    if not csv_files:
        print("[manual_import] manual_data 폴더에 CSV가 없습니다.")
        conn.close()
        return

    total = 0
    for path in csv_files:
        rows = _load_csv(path)
        by_indicator = {}
        for row in rows:
            by_indicator.setdefault(row["indicator_code"], []).append(row)

        for code, indicator_rows in by_indicator.items():
            first = indicator_rows[0]
            indicator_id = upsert_indicator(
                conn,
                code=code,
                name=first["indicator_name"],
                category=first["category"],
                unit=first["unit"],
                source="manual",
                region=first.get("region"),
            )
            pairs = [(r["date"], float(r["value"])) for r in indicator_rows]
            upsert_observations(conn, indicator_id, pairs)
            total += len(pairs)
            print(f"[manual_import] {code}: {len(pairs)}건 upsert 완료 ({path.name})")

    print(f"[manual_import] 총 {total}건 반영")
    conn.close()


if __name__ == "__main__":
    collect()
