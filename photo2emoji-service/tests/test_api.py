# -*- coding: utf-8 -*-
"""Photo2Emoji API 테스트 — 실제 FER 테스트 이미지로 end-to-end 검증."""
import io
import math
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.matching import FER, assign_emoji, build_mapping

FER_TEST_DIR = Path("/Users/chanjong/develop/python/인공지능 프로젝트/data/test")

pytestmark = pytest.mark.skipif(
    not FER_TEST_DIR.exists(), reason="FER 테스트 이미지가 로컬에 없음"
)


@pytest.fixture(scope="module")
def client():
    # with 블록이 startup 이벤트(모델 로드)를 실제로 실행한다
    with TestClient(app) as c:
        yield c


def _first_image(cls: str) -> Path:
    return sorted((FER_TEST_DIR / cls).glob("*.png"))[0]


# --- /health -------------------------------------------------------------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["model_loaded"] is True
    assert body["classes"] == FER


# --- /predict 구조 검증 ---------------------------------------------------

def test_predict_structure(client):
    img = _first_image("happy")
    r = client.post("/predict", files={"file": (img.name, img.read_bytes(), "image/png")})
    assert r.status_code == 200
    body = r.json()

    probs = body["probabilities"]
    assert set(probs.keys()) == set(FER)
    total = sum(probs.values())
    assert math.isclose(total, 1.0, abs_tol=0.01), f"확률 합이 1이 아님: {total}"

    assert body["predicted_class"] in FER
    assert 1 / 7 <= body["confidence"] <= 1.0  # argmax는 균등분포(1/7)보다 낮을 수 없다
    assert body["emoji"], "이모지가 비어 있음"
    assert body["emoji_name"]


@pytest.mark.parametrize("cls", ["happy", "surprised"])
def test_predict_plausible(client, cls):
    """정확한 클래스는 단정하지 않는다(모델 정확도 0.5954) — 구조와 범위만 검증."""
    img = _first_image(cls)
    r = client.post("/predict", files={"file": (img.name, img.read_bytes(), "image/png")})
    assert r.status_code == 200
    body = r.json()
    assert body["predicted_class"] in FER
    assert 1 / 7 <= body["confidence"] <= 1.0
    assert body["emoji"]


# --- 잘못된 입력 ----------------------------------------------------------

def test_predict_non_image(client):
    r = client.post("/predict", files={"file": ("x.txt", b"this is not an image", "text/plain")})
    assert 400 <= r.status_code < 500, f"4xx여야 하는데 {r.status_code}"


def test_predict_empty_file(client):
    r = client.post("/predict", files={"file": ("empty.png", b"", "image/png")})
    assert 400 <= r.status_code < 500


# --- 매칭 규칙 단위 테스트 (파이프라인 노트북 §6 예시와 동일해야 함) --------

@pytest.fixture(scope="module")
def mapping():
    return build_mapping(str(Path(__file__).resolve().parent.parent / "emoji_df.csv"))


def _vec(**kw):
    v = np.zeros(7)
    for cls, p in kw.items():
        v[FER.index(cls)] = p
    return v


def test_matching_happy_strong(mapping):
    """확신도 0.92 → happy의 강한(0.9) 이모지 계열."""
    emoji, cls, conf, name = assign_emoji(_vec(happy=0.92, neutral=0.05, surprised=0.03), mapping)
    assert cls == "happy" and math.isclose(conf, 0.92)
    row = mapping[mapping.emoji == emoji].iloc[0]
    assert row.intensity == 0.90, f"강한 이모지가 아님: {emoji} ({row.intensity})"


def test_matching_sad(mapping):
    emoji, cls, conf, name = assign_emoji(_vec(sad=0.88, fearful=0.07, neutral=0.05), mapping)
    assert cls == "sad"
    assert mapping[mapping.emoji == emoji].iloc[0].fer == "sad"


def test_matching_low_confidence_weak(mapping):
    """확신도 0.35 → happy의 약한(0.3) 이모지 계열."""
    emoji, cls, conf, name = assign_emoji(_vec(happy=0.35, neutral=0.33, sad=0.32), mapping)
    assert cls == "happy"
    row = mapping[mapping.emoji == emoji].iloc[0]
    assert row.intensity == 0.30, f"약한 이모지가 아님: {emoji} ({row.intensity})"


def test_matching_table_counts(mapping):
    """매핑표는 파이프라인 노트북과 동일하게 54/105."""
    assert len(mapping) == 54
    counts = mapping.fer.value_counts()
    assert counts["happy"] == 21 and counts["sad"] == 16 and counts["disgusted"] == 2
