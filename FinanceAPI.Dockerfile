FROM python:3.10.12

WORKDIR /api

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY ./api .

EXPOSE 8000

CMD ["make", "start_api"]