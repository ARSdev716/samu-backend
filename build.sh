#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

# Seed uniquement si la base est vide (évite les erreurs de redéploiement)
python manage.py shell -c "
from core.models import Hopital, Ambulance
if Hopital.objects.count() == 0:
    exec(open('seed_data.py').read())
    print('Seed exécuté.')
else:
    print('Base déjà initialisée — seed ignoré.')
"
