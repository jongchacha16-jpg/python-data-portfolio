# 뇌졸중(Stroke) 발병 예측 분석 (데이터사이언스 프로젝트)

건강검진/생활습관 데이터를 이용해 뇌졸중 발병 여부를 예측하는 팀 프로젝트입니다. (팀 과제 — 본 저장소에는 제 분석 파트를 포함합니다.)

## 문제 정의

- 타겟: `stroke` (뇌졸중 발병 여부, 이진 분류)
- 원본 데이터의 클래스 불균형(뇌졸중 발병 사례가 소수)이 핵심 과제
- 흡연 여부(`Unknown` 범주), `bmi` 결측치 처리가 주요 전처리 이슈

## 접근 방법

1. 결측값 처리: `bmi` 결측치, 흡연 컬럼의 `Unknown` 범주 처리
2. 이상치 탐색 (`gender` 등 범주형 변수 포함 EDA)
3. **언더샘플링**으로 클래스 균형 보정 (다수 클래스를 소수 클래스 규모로 맞춤)
4. Logistic Regression과 Random Forest(파라미터 튜닝 포함) 비교
5. 추가 분석: 혈당(126 이상=당뇨병 기준)·BMI(30 이상=비만 기준)·연령대(70대)별 서브그룹 분석, 중요 변수(bmi/age/avg_glucose_level) 제거 후 성능 변화 확인

## 결과

- Random Forest(교차검증) 기준 **평균 Accuracy 93.6%** (표준편차 2.1%), **Precision 1.0**, **Recall 87.3%**
- 파라미터를 세밀하게 튜닝하지 않은 기본 설정이 오히려 더 좋은 성능을 보임을 실험으로 확인
- 위 지표는 언더샘플링으로 균형을 맞춘 데이터셋 기준이며, 실제 서비스 적용 시에는 원본 클래스 비율에서의 재검증이 필요함을 인지하고 있음

## 파일 구성

- `데사프_분석_파트.ipynb` — 담당 분석 파트
- `stroke 최종본.ipynb` — 최종 통합 분석
- `stroke Logistic regression.ipynb`, `stroke Random Forest .ipynb`, `stroke_Random_Forest_(Z_score).ipynb`, `stroke critical x(Logistic).ipynb` — 모델별 실험
- `Stroke_UnderSampling.ipynb`, `data_under_sampling_.ipynb`, `stroke 추가 전처리(언더샘플링 수정).ipynb` — 언더샘플링 전처리 실험
- `산불 데이터 전처리.ipynb`, `programing_project(subgroup수정).ipynb` — 관련 서브 과제

## 참고

- 보건 데이터를 다루는 팀 과제입니다. 공개 전 데이터 출처의 라이선스와 학교/팀 정책을 확인하는 것을 권장합니다.
