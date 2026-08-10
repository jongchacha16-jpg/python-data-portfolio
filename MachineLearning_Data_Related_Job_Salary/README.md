# 데이터 관련 직무 연봉 분석 및 예측 (Data-Related Job Salary Analysis)

`ds_salaries.csv` 데이터를 이용해 데이터 관련 직무(Data Scientist, ML Engineer 등)의 연봉을 **설명(EDA/통계)** 하고 **예측(분류 모델)** 하는 프로젝트입니다.

## 문제 정의

- 데이터: 607행, `job_title`(49종), `employee_residence`/`company_location` 등 행 수 대비 카디널리티가 매우 높은 범주형 변수가 많은 작은 정형 데이터셋
- 타겟: `salary_in_usd`를 33/66 분위수로 `Low/Medium/High` 3-class 분류 문제로 프레이밍
- 핵심 이슈: `salary_currency`는 `salary_in_usd`의 파생 값이라 타겟 누수(leakage) 위험이 있다고 초기에 문서화됐지만, **실제 코드에는 계속 남아있었다.** 프로젝트 막바지에 CLAUDE.md와 실제 노트북 코드를 교차 검증하다가 이 괴리를 발견했고, `salary_currency`를 제거하고 재실행해 실제 영향을 정량적으로 확인했다.

## 접근 방법

0. 연도/경력수준/고용형태/원격근무 비율별 급여 분포 박스플롯으로 초기 EDA 진행
1. IQR 기반 이상치 제거 (607행 → 597행)
2. log/Box-Cox 변환 중 Shapiro-Wilk 검정으로 더 정규분포에 가까운 변환 선택
3. `pd.get_dummies(drop_first=True)` 원-핫 인코딩 (다중공선성 방지). 회귀 섹션에서 `drop_first=False`로 인코딩해 VIF가 수백만대로 폭증하는 버그를 VIF 진단으로 발견 → `drop_first=True`로 수정
4. Random Forest / XGBoost 비교, `RandomizedSearchCV` 하이퍼파라미터 튜닝
5. PCA는 시도했으나 비효율적임을 확인(105개 성분 필요, R² -10 수준으로 악화) → XGBoost `feature_importances_` 누적 95% 기준 변수 선택으로 대체
6. SMOTE + `class_weight='balanced'` 클래스 불균형 보정을 시도했으나 오히려 성능 저하 확인(정확도 0.5917→0.5583) → 기본 적용하지 않기로 결정
7. `job_title`(49종) 단순화(`job_group`, 7종) 대안도 검증했으나 정확도가 더 낮아(0.5667) 채택하지 않음
8. **`salary_currency` 제거 후 재검증**: 회귀 R²는 소폭 하락(0.4319→0.4134)했지만, 분류 정확도는 오히려 상승(RF 0.5917→0.6083, XGBoost 0.6833→0.6917) — 해당 컬럼이 분류 문제에서는 신호가 아니라 노이즈에 가까웠음을 확인
9. 전체 피처 모델(0.6750) vs 변수중요도 축소 모델(0.6917)을 나란히 비교해 차원 축소 효과를 재확인

## 결과 (리키지 제거 후 최종 baseline)

- 3-class(Low/Medium/High) 분류 정확도 **XGBoost 0.6917** (축소 피처 28개), **Random Forest 0.6083**
- High/Low는 F1 0.7 내외로 비교적 안정적, **Medium 클래스는 구조적으로 가장 분류가 어려운 클래스**로 일관되게 확인 (F1 0.5~0.6)
- Linear Regression 기준 R² ≈ 0.4134

## 파일 구성

- `ds_salaries.csv` — 원본 데이터
- `MachineLearning_Team5.ipynb` — 최종 통합 분석 노트북 (EDA → 전처리 → 회귀/분류 모델링 → job_group 실험 → salary_currency 리키지 사후 검증까지 전체 파이프라인)
- `MachineLearning_Team5_1.ipynb` — 초기 실험 초안(직무 간소화·이진 라벨링 등 아이디어 스케치). 유효했던 아이디어(`simplify_job_title`)는 최종 노트북에 반영됨
- `CLAUDE.md` — 최종 노트북에서 실제로 검증된 분석 규칙/실측 baseline 정리
- `CLAUDE_PROPOSED.md` — 처음부터 이 프로젝트를 설계한다면 따를 방법론 제안본 (설명적 분석과 예측적 모델링을 명확히 분리하는 접근)

## 배운 점

- 파생 변수를 피처로 넣었을 때의 데이터 누수를 정량적으로 탐지하고, 실제로 제거해 영향을 측정한 경험. "리키지라고 알고 있었다"와 "실제로 코드에서 제거되어 있다"는 다른 문제라는 걸 문서-코드 교차검증으로 확인함
- 리키지 컬럼을 제거했을 때 분류 성능이 오히려 개선된 것은, 해당 컬럼이 실제로는 노이즈에 가까웠다는 뜻 — "누수 위험이 있다고 해서 반드시 성능에 도움이 되는 건 아니다"라는 인사이트
- PCA, SMOTE처럼 "일반적으로 도움이 될 것 같은" 기법이 특정 데이터셋에서는 오히려 성능을 해칠 수 있음을 실험으로 확인하고, 근거 없이 채택하지 않는 판단 기준을 세움
- 여러 실험 노트북(초안/중간본/최종본)이 쌓였을 때, 셀 단위로 비교해 중복을 제거하고 하나의 최종본으로 통합하는 정리 과정 자체도 프로젝트 산출물로 문서화함
