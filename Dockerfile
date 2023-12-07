FROM python:3.10-alpine

ENV API_PORT 8000

EXPOSE $API_PORT

WORKDIR /app

RUN apk add --no-cache tzdata gcc libc-dev libffi-dev
ENV TZ=Europe/Lisbon

COPY . .

RUN pip install --no-cache-dir --upgrade pip

RUN pip install --no-cache-dir poetry

RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

CMD ["tesla-smart-charger"]
