# -*- coding: utf-8 -*-
"""Photo2Emoji 서비스 — 사진 → 감정 → 이모지 (FastAPI).

`인공지능 프로젝트`의 재학습된 CNN(Run B, 전체 test 정확도 0.5954)과
이모지 매칭 규칙(§6)을 HTTP API 로 서빙한다.

  POST /predict : 이미지 업로드 → 7차원 감정 벡터 + 확신도 + 할당 이모지
  GET  /health  : 모델 로드 상태
  GET  /        : 웹 데모 페이지 (static/index.html)
"""
import io
import os
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from .matching import FER, assign_emoji, build_mapping

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = os.environ.get("MODEL_PATH", str(BASE_DIR / "model" / "model_fixed.keras"))
EMOJI_CSV = os.environ.get("EMOJI_CSV", str(BASE_DIR / "emoji_df.csv"))

_model = None
_mapping = None


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """모델과 매핑표는 프로세스당 1회만 로드한다 (요청마다 로드하면 수 초씩 걸린다)."""
    global _model, _mapping
    import tensorflow as tf  # 지연 임포트 — 테스트 수집 시 TF 로딩 비용 회피
    _model = tf.keras.models.load_model(MODEL_PATH)
    _mapping = build_mapping(EMOJI_CSV)
    yield


app = FastAPI(title="Photo2Emoji", version="1.0.0", lifespan=_lifespan)


@app.get("/health")
def health():
    return {
        "status": "ok" if _model is not None else "model_not_loaded",
        "model_loaded": _model is not None,
        "classes": FER,
    }


def _preprocess(data: bytes) -> np.ndarray:
    """임의 크기/색상의 이미지를 학습 입력 형식(48×48 그레이스케일, 1/255)으로 변환."""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=422, detail="올바른 이미지 파일이 아닙니다.")
    img = img.convert("L").resize((48, 48), Image.LANCZOS)
    arr = np.asarray(img, dtype=np.float32) / 255.0
    return arr.reshape(1, 48, 48, 1)


@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if _model is None:
        raise HTTPException(status_code=503, detail="모델이 아직 로드되지 않았습니다.")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="빈 파일입니다.")
    x = _preprocess(data)
    proba = _model.predict(x, verbose=0)[0]
    emoji, cls, conf, emoji_name = assign_emoji(proba, _mapping)
    return {
        "filename": file.filename,
        "probabilities": {c: round(float(p), 4) for c, p in zip(FER, proba)},
        "predicted_class": cls,
        "confidence": round(conf, 4),
        "emoji": emoji,
        "emoji_name": emoji_name,
        "model": "Run B (full-test acc 0.5954)",
    }


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "static" / "index.html")


app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
