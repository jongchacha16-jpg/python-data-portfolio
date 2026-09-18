FROM python:3.11-slim

WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY static/ static/
COPY emoji_df.csv .
# 가중치는 이미지에 포함 (빌드 컨텍스트에 model/model_fixed.keras 필요)
COPY model/ model/

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
