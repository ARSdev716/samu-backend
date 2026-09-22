"""
Permissions personnalisées par rôle — sécurise les endpoints métier.

- Le SOS est public (pas d'authentification nécessaire).
- Seul un médecin régulateur (ou admin) peut envoyer une ambulance.
- Seule l'équipe d'intervention peut mettre à jour le statut d'une mission.
"""

from rest_framework.permissions import BasePermission, SAFE_METHODS


class AccesSosPublic(BasePermission):
    """UC_02 — Le bouton SOS doit être accessible SANS authentification."""

    def has_permission(self, request, view):
        return True


class EstAuthentifie(BasePermission):
    """Vérifie simplement que l'utilisateur est authentifié."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated


class EstRegulateurOuAdmin(BasePermission):
    """
    UC_03 — Seul un médecin régulateur ou un administrateur peut :
    - Envoyer une ambulance (action 'envoyer')
    - Créer/modifier/supprimer des missions
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in (
            "medecin_regulateur",
            "administrateur",
        )


class EstEquipeIntervention(BasePermission):
    """
    UC_04 — Seule l'équipe d'intervention peut mettre à jour
    le statut d'une mission sur le terrain.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.role in (
            "equipe_intervention",
            "medecin_regulateur",
            "administrateur",
        )


class LectureOuRegulateur(BasePermission):
    """
    Lecture ouverte à tout utilisateur authentifié.
    Écriture réservée au régulateur / admin.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.role in (
            "medecin_regulateur",
            "administrateur",
        )
