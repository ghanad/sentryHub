#!/bin/bash

mkdir -p /code/data
chmod 777 /code/data

echo "Running makemigrations..."
python manage.py makemigrations

echo "Running migrate..."
python manage.py migrate

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Checking for superuser..."
python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); exit(0 if User.objects.filter(username='${DJANGO_SUPERUSER_USERNAME}').exists() else 1)" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "Creating a superuser..."
    python manage.py createsuperuser --noinput
fi

echo "Starting server..."
python manage.py runserver 0.0.0.0:8000
