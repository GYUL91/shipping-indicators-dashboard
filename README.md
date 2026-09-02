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
- **조회기간 최대화**: 각 소스가 실제로 제공하는 만큼 전체 이력을 수집 (SCFI/CCFI/BDI는 소스 자체가
  2014년부터만 제공, 국내 항로별 지수는 여러 번 요청을 이어붙여 실제 시작월인 2019-01까지 확보,
  EIA 유가는 페이지네이션으로 전체 이력 수집)
- **이벤트 주석**: 리먼사태·수에즈 봉쇄·홍해 사태 등 주요 국제 이벤트를 `docs/data/events.json`에
  큐레이션해 차트에 점선으로 표시, 클릭하면 설명 표시 (직접 항목 추가/수정 가능)
- **운임지수 비교 모드**: 좌측 체크박스로 여러 운임지수를 선택하면 공통 구간을 기준으로
  시작값=100 정규화한 비교 차트 렌더링
- **자동 인사이트**: `export/export_json.py`가 지표별 최신값/역대 최고·최저/전년동기대비 변화율을
  계산해 JSON에 포함, 대시보드 상단 "데이터로 보는 인사이트" 패널이 이를 바탕으로 해설 문장을 생성

## 자동화

`.github/workflows/collect.yml`이 매일 1회 수집 → export → commit → push를 수행합니다.
Repository Settings > Secrets에 `EIA_API_KEY`를 등록해야 유가 지표가 자동 갱신됩니다.
