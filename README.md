# 해운 지표 대시보드

해운 산업 관련 지표(운임 지수, 물동량/처리량, 선박/선대, 유가/연료비)를 수집해
SQLite DB에 저장하고, GitHub Pages 정적 대시보드로 시각화하는 프로젝트입니다.

## 지표 출처 및 수집 방식

| 카테고리 | 지표 예시 | 출처 | 수집 방식 |
|---|---|---|---|
| 유가/연료비 | Brent/WTI 유가, 미국 디젤 소매가 | EIA (미국 에너지정보청) | 자동 (API 키 필요) |
| 물동량/처리량 | 컨테이너 항만 처리량(TEU) | World Bank | 자동 (API 키 불필요) |
| 운임 지수 | BDI, SCFI, CCFI | Baltic Exchange / 상하이해운거래소 | **수동 CSV 입력** (유료 구독 전용, 무료 API 없음) |
| 선박/선대 | 세계 상선대 규모 | UNCTAD | **수동 CSV 입력** (연 1회 발표) |

BDI/SCFI/CCFI 등은 공식 무료 API가 없어 `manual_data/*.csv`에 값을 직접 채워넣는 방식으로 반영합니다.

## 설치

```bash
pip install -r requirements.txt
```

EIA 유가 자동 수집을 쓰려면 무료 API 키를 발급받아 환경변수로 설정하세요.
https://www.eia.gov/opendata/register.php

```bash
export EIA_API_KEY=your_key_here
```

키가 없어도 나머지 파이프라인(물동량, 수동입력)은 정상 동작합니다.

## 사용법

```bash
# 전체 수집 + JSON export
python collectors/run_all.py

# 개별 실행
python collectors/fuel_prices.py
python collectors/cargo_volume.py
python collectors/manual_import.py
python export/export_json.py
```

`manual_data/freight_indices_template.csv`를 참고해 BDI/SCFI/CCFI 등 실제 값을 채워넣은 뒤
`python collectors/manual_import.py`를 실행하면 DB에 반영됩니다.

## 대시보드

`docs/index.html`이 `docs/data/all.json`을 fetch해 Chart.js로 시각화하는 정적 페이지입니다.
GitHub Pages에서 `docs/` 폴더를 배포 루트로 지정하면 바로 서비스됩니다.

## 자동화

`.github/workflows/collect.yml`이 매일 1회 수집 → export → commit → push를 수행합니다.
Repository Settings > Secrets에 `EIA_API_KEY`를 등록해야 유가 지표가 자동 갱신됩니다.
