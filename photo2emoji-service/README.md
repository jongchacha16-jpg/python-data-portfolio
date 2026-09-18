# Photo2Emoji 서비스 — 사진 → 감정 → 이모지 API

**`인공지능 프로젝트`의 파이프라인을 실제 서비스로 만든 것**입니다.
3년 묵은 과제를 분석·재학습으로 완성한 뒤(2026-09-18), 그 산출물 — 재학습된
CNN 가중치(Run B)와 이모지 매칭 규칙 — 을 FastAPI로 서빙합니다.
노트북에서만 돌던 파이프라인이 이제 HTTP 요청 한 번으로 동작합니다.

## 아키텍처

```
[브라우저 / curl]
      │  POST /predict  (이미지 업로드, 임의 크기·색상)
      ▼
[FastAPI (app/main.py)]
      │  ① 전처리: 48×48 그레이스케일 변환, 1/255 정규화
      ▼
[CNN — model/model_fixed.keras]          ← 인공지능 프로젝트 Run B 재학습 가중치
      │  ② 7차원 softmax 확률 벡터
      ▼
[매칭 규칙 — app/matching.py]            ← 이모지_매칭_파이프라인.ipynb §6 그대로
      │  ③ argmax 클래스 → 확신도와 강도가 가장 가까운 이모지
      ▼
JSON 응답: 확률 벡터 + 클래스 + 확신도 + 이모지
```

- `GET /` — 웹 데모 페이지 (사진 올리면 확률 막대 + 이모지)
- `GET /health` — 모델 로드 상태
- `POST /predict` — 예측 API

## 실행

### 로컬 (venv)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
# 브라우저에서 http://127.0.0.1:8000
```

### Docker

```bash
docker build -t photo2emoji .
docker run -p 8000:8000 photo2emoji
```

## 실측 응답 (2026-09-18, 실제 실행 기록)

```bash
$ curl -s http://127.0.0.1:8777/health
{"status":"ok","model_loaded":true,"classes":["angry","disgusted","fearful","happy","neutral","sad","surprised"]}

$ curl -s -F "file=@data/test/happy/im0.png" http://127.0.0.1:8777/predict
{"filename":"im0.png",
 "probabilities":{"angry":0.0007,"disgusted":0.0,"fearful":0.0001,"happy":0.9973,
                  "neutral":0.0008,"sad":0.0,"surprised":0.0011},
 "predicted_class":"happy","confidence":0.9973,
 "emoji":"😁","emoji_name":"beaming face with smiling eyes",
 "model":"Run B (full-test acc 0.5954)"}
```

확신도 0.9973 → 매칭 규칙이 강도 0.9의 강한 이모지(😁)를 고르는 것까지
설계대로 동작합니다. 반대로 아래는 **모델이 틀리는 실제 사례**입니다:

```bash
$ curl -s -F "file=@data/test/sad/im0.png" http://127.0.0.1:8777/predict
{... "predicted_class":"angry","confidence":0.5928,"emoji":"😠" ...}   # 정답은 sad
```

이건 서비스 버그가 아니라 1단계 CNN의 알려진 혼동 패턴(sad→angry)이 그대로
드러난 것입니다 — 재학습 혼동행렬에서 sad 재현율은 0.464였습니다.

잘못된 입력은 500이 아니라 4xx로 처리됩니다:

```bash
$ curl -s -w "HTTP %{http_code}" -F "file=@not_an_image.txt" .../predict
{"detail":"올바른 이미지 파일이 아닙니다."}  HTTP 422
```

## 테스트

```bash
python -m pytest tests/ -v
```

실행 결과 (2026-09-18): **10 passed** —
`/health`, `/predict` 응답 구조(확률 합 ≈ 1, 클래스 유효성, 확신도 범위 1/7~1.0),
비이미지·빈 파일 4xx 처리, 매칭 규칙 단위 테스트(확신도 0.92 → 강도 0.9 이모지,
0.35 → 강도 0.3 이모지, 매핑표 54/105 및 클래스별 개수가 파이프라인 노트북과 일치).

정확한 예측 클래스는 테스트에서 단정하지 않습니다 — 모델 정확도가 0.5954이므로
특정 이미지의 정답 여부를 단정하면 취약한(flaky) 테스트가 됩니다.

## 모델 출처와 재현

- 가중치 `model/model_fixed.keras`는 **용량 문제로 저장소에 포함하지 않습니다** (gitignore).
- 재현 경로: [`../인공지능 프로젝트/build/build_fer_retrain.py`](../인공지능%20프로젝트/build/build_fer_retrain.py)
  — FER 데이터셋(Kaggle `ananthu017/emotion-detection-fer`)으로 재학습하면
  `retrain_artifacts/model_fixed.keras`가 생성됩니다 (로컬 CPU 약 18분).
- 재학습 배경·Run A/B 비교·혼동행렬: [`../인공지능 프로젝트/README.md`](../인공지능%20프로젝트/README.md)

## 한계 (정직하게)

1. **서비스 품질의 상한은 1단계 CNN 정확도 0.5954입니다.** 매칭 규칙이 아무리 잘
   동작해도 10장 중 4장은 틀린 클래스로 이모지가 배정됩니다.
2. **FER 도메인(48×48 그레이스케일, 얼굴이 프레임에 꽉 참) 밖에서는 더 떨어집니다.**
   얼굴 검출/크롭 단계가 없어서, 실세계 사진(컬러·고해상도·얼굴이 화면 일부)은
   전체 이미지가 통째로 48×48로 축소됩니다 — 이 경우의 성능은 측정하지 않았습니다. `[미검증]`
3. **단일 얼굴 가정.** 여러 명이 있는 사진에 대한 동작은 정의되지 않았습니다.

## Docker 빌드 검증 기록 (2026-09-18)

`docker build` 실제 성공(python:3.11-slim, arm64), 컨테이너 기동 후 실측:

```bash
$ docker run -d -p 8778:8000 photo2emoji:test
$ curl -s http://127.0.0.1:8778/health
{"status":"ok","model_loaded":true, ...}
$ curl -s -F "file=@data/test/surprised/im0.png" http://127.0.0.1:8778/predict
{... "predicted_class":"surprised","confidence":0.8633,"emoji":"😲" ...}
```

검증 후 컨테이너·이미지는 정리했습니다. 가중치가 gitignore라 **빌드 컨텍스트에
`model/model_fixed.keras`를 먼저 채워야** 빌드가 됩니다(위 재현 경로 참고).

## 파일 구성

```
app/main.py       FastAPI 엔드포인트 (predict/health/데모)
app/matching.py   이모지 매칭 규칙 — 파이프라인 노트북 §6과 동일 로직
static/index.html 웹 데모 (CDN 없는 단일 파일)
tests/test_api.py pytest 스위트 (10개)
model/            가중치 (git 미포함 — 위 재현 경로 참고)
emoji_df.csv      이모지 메타데이터 (매핑표 원천)
Dockerfile        컨테이너 빌드
```
