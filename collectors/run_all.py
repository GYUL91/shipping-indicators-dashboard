"""전체 수집 파이프라인 오케스트레이션: DB 초기화 -> 각 수집기 실행 -> JSON export."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "export"))

from db import init_db
import fuel_prices
import cargo_volume
import manual_import


def main():
    init_db()

    print("=== 유가/연료비 (EIA) ===")
    fuel_prices.collect()

    print("=== 물동량 (World Bank) ===")
    cargo_volume.collect()

    print("=== 수동 입력 (운임지수/선대) ===")
    manual_import.collect()

    print("=== JSON export ===")
    import export_json
    export_json.export()

    print("완료.")


if __name__ == "__main__":
    main()
