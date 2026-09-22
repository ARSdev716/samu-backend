"""
Données de démonstration — Hôpitaux et ambulances de Yaoundé.

Usage :
    python manage.py shell < seed_data.py

Insère les établissements de santé réels avec leurs coordonnées GPS,
ainsi qu'une flotte d'ambulances de test positionnées dans la ville.
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ars_backend.settings")
django.setup()

from core.models import Hopital, Ambulance, Utilisateur

# ── Hôpitaux de Yaoundé ──

hopitaux = [
    {
        "nom": "Centre des Urgences de Yaoundé (CURY)",
        "latitude": 3.8480,
        "longitude": 11.5021,
        "capacite_lits": 50,
        "telephone": "+237 222 231 247",
    },
    {
        "nom": "Hôpital Central de Yaoundé",
        "latitude": 3.8612,
        "longitude": 11.5160,
        "capacite_lits": 400,
        "telephone": "+237 222 231 421",
    },
    {
        "nom": "Hôpital Général de Yaoundé",
        "latitude": 3.8686,
        "longitude": 11.5188,
        "capacite_lits": 300,
        "telephone": "+237 222 223 020",
    },
    {
        "nom": "Centre Hospitalier Universitaire (CHU)",
        "latitude": 3.8667,
        "longitude": 11.5000,
        "capacite_lits": 250,
        "telephone": "+237 222 231 850",
    },
    {
        "nom": "Hôpital Gynéco-Obstétrique et Pédiatrique",
        "latitude": 3.8617,
        "longitude": 11.5172,
        "capacite_lits": 200,
        "telephone": "+237 222 231 672",
    },
    {
        "nom": "Hôpital de la Caisse (CNPS)",
        "latitude": 3.8580,
        "longitude": 11.5040,
        "capacite_lits": 120,
        "telephone": "+237 222 231 550",
    },
    {
        "nom": "Centre Médical La Cathédrale",
        "latitude": 3.8540,
        "longitude": 11.5155,
        "capacite_lits": 60,
        "telephone": "+237 222 220 800",
    },
    {
        "nom": "Hôpital de District de Biyem-Assi",
        "latitude": 3.8345,
        "longitude": 11.4855,
        "capacite_lits": 80,
        "telephone": "+237 222 312 000",
    },
]

print("--- Insertion des hôpitaux ---")
for h in hopitaux:
    obj, created = Hopital.objects.update_or_create(
        nom=h["nom"],
        defaults=h,
    )
    statut = "CREE" if created else "existant"
    print(f"  [{statut}] {obj.nom}")

# ── Ambulances ──

ambulances = [
    {
        "matricule": "AMB-YDE-001",
        "equipement": "SMUR complet, DSA, oxygène, brancard motorisé",
        "statut": "disponible",
        "latitude": 3.8510,
        "longitude": 11.5050,
    },
    {
        "matricule": "AMB-YDE-002",
        "equipement": "Premiers secours, oxygène, attelles",
        "statut": "disponible",
        "latitude": 3.8650,
        "longitude": 11.5180,
    },
    {
        "matricule": "AMB-YDE-003",
        "equipement": "SMUR, défibrillateur, monitoring",
        "statut": "disponible",
        "latitude": 3.8420,
        "longitude": 11.4920,
    },
    {
        "matricule": "AMB-YDE-004",
        "equipement": "VSL, premiers secours basiques",
        "statut": "en_mission",
        "latitude": 3.8580,
        "longitude": 11.5100,
    },
    {
        "matricule": "AMB-YDE-005",
        "equipement": "SMUR complet, incubateur néonatal",
        "statut": "maintenance",
        "latitude": 3.8480,
        "longitude": 11.5021,
    },
]

print("\n--- Insertion des ambulances ---")
for a in ambulances:
    obj, created = Ambulance.objects.update_or_create(
        matricule=a["matricule"],
        defaults=a,
    )
    statut = "CREE" if created else "existant"
    print(f"  [{statut}] {obj.matricule} ({obj.get_statut_display()})")

# ── Utilisateurs de test ──

utilisateurs = [
    {
        "username": "regulateur1",
        "password": "ArsSecure2026!",
        "role": "medecin_regulateur",
        "first_name": "Jean",
        "last_name": "Mbarga",
    },
    {
        "username": "admin1",
        "password": "ArsSecure2026!",
        "role": "administrateur",
        "first_name": "Admin",
        "last_name": "ARS",
    },
]

ambulanciers = [
    {"username": "AMB-YDE-001", "first_name": "Paul", "last_name": "Nkoulou"},
    {"username": "AMB-YDE-002", "first_name": "Marc", "last_name": "Essomba"},
    {"username": "AMB-YDE-003", "first_name": "Jean", "last_name": "Fouda"},
    {"username": "AMB-YDE-004", "first_name": "Pierre", "last_name": "Atangana"},
    {"username": "AMB-YDE-005", "first_name": "Samuel", "last_name": "Owona"},
]

for amb in ambulanciers:
    amb["password"] = "ArsSecure2026!"
    amb["role"] = "equipe_intervention"
    utilisateurs.append(amb)

print("\n--- Insertion des utilisateurs de test ---")
for u in utilisateurs:
    pwd = u.pop("password")
    obj, created = Utilisateur.objects.get_or_create(
        username=u["username"],
        defaults=u,
    )
    if created:
        obj.set_password(pwd)
        obj.save()
        print(f"  [CREE] {obj.username} ({obj.get_role_display()}) — mdp: ArsSecure2026!")
    else:
        print(f"  [existant] {obj.username}")

print("\n--- Assignation des ambulanciers aux véhicules ---")
for amb in Ambulance.objects.all():
    user = Utilisateur.objects.filter(username=amb.matricule).first()
    if user:
        amb.ambulancier = user
        amb.save()
        print(f"  [{amb.matricule}] assigné à {user.first_name} {user.last_name}")

print("\n--- Seed terminé ---")
print(f"  {Hopital.objects.count()} hôpitaux")
print(f"  {Ambulance.objects.count()} ambulances")
print(f"  {Utilisateur.objects.count()} utilisateurs")
