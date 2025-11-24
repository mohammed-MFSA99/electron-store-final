#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# جمع الملفات الثابتة
python manage.py collectstatic --no-input

# تحديث قاعدة البيانات
python manage.py migrate