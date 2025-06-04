FROM python:3.10.12

ENV DATABASE_URL="postgresql://{0}:{1}@{2}:{3}/verix_finance_bot"
ENV DATABASE_ENDPOINT="verix.cx6ya8kam5qw.us-east-2.rds.amazonaws.com"
ENV DATABASE_PORT="5432"
ENV DATABASE_USERNAME="jvict"
ENV DATABASE_PASSWORD="REDACTED"

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 80

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]