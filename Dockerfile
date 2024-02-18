FROM python:3.9

ENV API_PORT 8000

EXPOSE $API_PORT

WORKDIR /app

ENV TZ=Europe/Lisbon

COPY . .

RUN pip install --no-cache-dir --upgrade pip

RUN pip install --no-cache-dir poetry

RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

RUN rm /app/config.json

CMD [ "tesla-smart-charger", "--monitor", "--verbose" ]