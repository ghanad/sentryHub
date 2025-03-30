FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY requirements.txt /code/
RUN pip install -r requirements.txt
RUN pip install django-createsuperuser

COPY . /code/

EXPOSE 8000

#COPY entrypoint.sh /code/
RUN chmod +x /code/entrypoint.sh
