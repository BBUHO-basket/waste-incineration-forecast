# Waste Incineration Forecast

## 프로젝트 소개

서울시 자원회수시설의 월별 운영 데이터를 활용하여 **폐기물 반입량과 소각량을 예측하는 AI 기반 웹 서비스**입니다.

본 프로젝트는 자원회수시설 운영자의 관점에서 미래의 폐기물 반입량을 예측하고, 이를 기반으로 소각량과 CO₂ 배출량을 추정하여 효율적인 시설 운영 의사결정을 지원하는 것을 목표로 합니다.

---

## 프로젝트 배경

자원회수시설은 계절과 지역에 따라 폐기물 반입량이 크게 변합니다.

반입량을 미리 예측할 수 있다면

- 시설 운영 계획 수립
- 소각량 예측
- 온실가스 배출량 추정
- 배출권 관리

등 다양한 의사결정에 활용할 수 있습니다.

---

## 주요 기능

- 월별 폐기물 반입량 예측
- 월별 소각량 예측
- AI 모델(XGBoost) 기반 예측
- 웹에서 예측 결과 확인
- 시설별 예측 지원

---

## 사용 기술

### Backend

- Django
- Python

### Machine Learning

- XGBoost
- Scikit-learn
- Pandas
- NumPy

### Database

- MySQL

### Visualization

- Matplotlib

---

## 데이터

사용 데이터

- 서울시 자원회수시설 운영현황
- 생활폐기물 발생 데이터
- 온실가스 관련 공공데이터

대상 시설

- 강남
- 노원
- 마포
- 양천

---

## 머신러닝 모델

반입량 예측 모델

- XGBoost Regressor

사용 Feature

- Previous Month Incoming
- Previous 2 Months Average
- Previous 3 Months Average
- Historical Monthly Average
- Historical Monthly Incineration Rate
- Facility

---

## 프로젝트 구조

```
waste-incineration-forecast

├── board
├── config
├── docs
├── member
├── ml_models
├── static
├── templates
├── train_incoming_model.py
├── train_incineration_model.py
├── manage.py
└── README.md
```

---

## 향후 개선 사항

- CO₂ 배출량 예측 고도화
- Streamlit 대시보드 구축
- Docker 배포
- AWS 배포
- 모델 자동 재학습 파이프라인 구축

---

## 개발자

Industrial Engineering
BBUHO-basket

Python | Django | Machine Learning | Data Analysis