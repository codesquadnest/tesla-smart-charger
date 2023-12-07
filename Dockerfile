FROM python:3.10-alpine

ENV API_PORT 8000

EXPOSE $API_PORT

WORKDIR /app

RUN apk add --no-cache tzdata
ENV TZ=Europe/Lisbon

RUN pip install --no-cache-dir --upgrade pip

RUN pip install --no-cache-dir poetry

COPY . /app

RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

CMD ["tesla-smart-charger"]
