# 해운 지표 대시보드

해운 산업 관련 지표(운임 지수, 물동량/처리량, 선박/선대, 유가/연료비)를 수집해
SQLite DB에 저장하고, GitHub Pages 정적 대시보드로 시각화하는 프로젝트입니다.

## 지표 출처 및 수집 방식

| 카테고리 | 지표 예시 | 출처 | 수집 방식 |
|---|---|---|---|
| 운임 지수 | BDI, SCFI, CCFI, 국내 해상운임지수(수출입 x 6개 항로) | 국가물류통합정보센터(NLIC, 국토교통부) | 자동 (API 키 불필요) |
| 유가/연료비 | Brent/WTI 유가, 미국 디젤 소매가 | EIA (미국 에너지정보청) | 자동 (API 키 필요) |
| 물동량/처리량 | 컨테이너 항만 처리량(TEU) | World Bank | 자동 (API 키 불필요) |
| 선박/선대 | 세계 상선대 규모 | UNCTAD | **수동 CSV 입력** (연 1회 발표) |

운임 지수는 [nlic.go.kr](https://www.nlic.go.kr/nlic/transInPortCt.action)(국외: SCFI/CCFI/BDI, 한국관세물류협회 자료)와
[seaDmstcOcn.action](https://www.nlic.go.kr/nlic/seaDmstcOcn.action)(국내: 관세청 수출입무역통계 기반)의 검색 폼을
그대로 HTTP POST로 호출해 자동 수집합니다(`collectors/freight_indices.py`).
선대 통계처럼 정말 무료 소스가 없는 지표만 `manual_data/*.csv`에 직접 채워넣는 방식으로 반영합니다.

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

`docs/index.html`이 `docs/data/all.json`(지표+통계)과 `docs/data/events.json`(국제 이벤트)을
fetch해 Chart.js로 시각화하는 정적 페이지입니다. GitHub Pages에서 `docs/` 폴더를 배포 루트로
지정하면 바로 서비스됩니다. 배포 주소: https://gyul91.github.io/shipping-indicators-dashboard/

기능:
- **조회기간 최대화 + 기간 선택**: 각 소스가 실제로 제공하는 만큼 전체 이력을 수집하고
  (SCFI/CCFI/BDI는 소스 자체가 2014년부터만 제공, 국내 항로별 지수는 여러 번 요청을 이어붙여
  실제 시작월인 2019-01까지 확보, EIA 유가는 페이지네이션으로 전체 이력 수집),
  차트 위 전체/10년/5년/3년/1년/6개월 버튼으로 조회 기간을 즉시 좁혀볼 수 있음
- **이벤트 주석**: 리먼사태·수에즈 봉쇄·홍해 사태 등 주요 국제 이벤트를 `docs/data/events.json`에
  큐레이션해 차트에 점선으로 표시, 클릭하면 설명 표시 (직접 항목 추가/수정 가능)
- **출처 링크**: 지표 선택 시 원본 데이터를 가져온 페이지로 바로 이동할 수 있는 링크 표시
  (`indicators.source_url` 컬럼, 각 수집기가 채움)
- **지표 설명**: BDI/SCFI/CCFI 등 주요 지표를 선택하면 무엇을 의미하는지, 어떻게 해석하면
  좋은지, 비슷해 보이는 지표(SCFI vs CCFI)와 어떻게 다른지 설명 패널 표시
  (`docs/index.html`의 `DESCRIPTIONS` 객체, 코드 패턴 기반 fallback 포함)
- **비교 모드**: 좌측 체크박스로 여러 지표 선택 시
  - 운임 지수: 공통 구간 기준 시작값=100 정규화 비교 차트
  - 물동량/처리량: 원자료 그대로의 선 그래프 또는 연도별 누적 막대그래프 중 선택
- **자동 인사이트**: `export/export_json.py`가 지표별 최신값/역대 최고·최저/전년동기대비 변화율을
  계산해 JSON에 포함, 대시보드 상단 "데이터로 보는 인사이트" 패널이 이를 바탕으로 해설 문장을 생성

## 자동화

`.github/workflows/collect.yml`이 매일 1회 수집 → export → commit → push를 수행합니다.
Repository Settings > Secrets에 `EIA_API_KEY`를 등록해야 유가 지표가 자동 갱신됩니다.
