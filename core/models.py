import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class Utilisateur(AbstractUser):
    """UC_01 - S'authentifier : chaque rôle a un espace de travail dédié."""

    class Role(models.TextChoices):
        USAGER = "usager", "Usager (victime/témoin)"
        PERMANENCIER = "permanencier", "Permanencier"
        MEDECIN_REGULATEUR = "medecin_regulateur", "Médecin régulateur"
        EQUIPE_INTERVENTION = "equipe_intervention", "Équipe d'intervention"
        HOPITAL = "hopital", "Hôpital récepteur"
        ADMINISTRATEUR = "administrateur", "Administrateur"

    role = models.CharField(max_length=30, choices=Role.choices, default=Role.USAGER)
    telephone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


class Hopital(models.Model):
    nom = models.CharField(max_length=150)
    latitude = models.FloatField()
    longitude = models.FloatField()
    capacite_lits = models.PositiveIntegerField(default=0)
    telephone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.nom


class Ambulance(models.Model):
    """UC_03 - Envoyer une ambulance : le régulateur voit position + statut en temps réel."""

    class Statut(models.TextChoices):
        DISPONIBLE = "disponible", "Disponible"
        EN_MISSION = "en_mission", "En mission"
        MAINTENANCE = "maintenance", "En maintenance"
        EN_PANNE = "en_panne", "En panne"

    ambulancier = models.ForeignKey(
        Utilisateur, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ambulance_assignee",
        limit_choices_to={"role": "equipe_intervention"},
        help_text="Ambulancier assigné à ce véhicule"
    )
    matricule = models.CharField(max_length=30, unique=True)
    equipement = models.CharField(max_length=255, blank=True)
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.DISPONIBLE)
    # Position mise à jour et lue en temps réel côté app via Supabase Realtime.
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    derniere_maj_position = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.matricule} ({self.get_statut_display()})"


class Alerte(models.Model):
    """UC_02 - Déclencher une alerte."""

    class Gravite(models.TextChoices):
        P1 = "P1", "Urgence vitale"
        P2 = "P2", "Urgence relative"
        P3 = "P3", "Non urgent"

    class StatutAlerte(models.TextChoices):
        EN_ATTENTE = "en_attente", "En attente de prise en charge"
        PRISE_EN_CHARGE = "prise_en_charge", "Prise en charge par un régulateur"
        ANNULEE = "annulee", "Annulée"

    id_suivi = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    usager = models.ForeignKey(
        Utilisateur, on_delete=models.SET_NULL, null=True, blank=True, related_name="alertes"
    )
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    adresse_manuelle = models.CharField(
        max_length=255, blank=True, help_text="Saisie si le GPS est indisponible (scénario 3b)"
    )
    description = models.TextField(blank=True)
    telephone_victime = models.CharField(
        max_length=20, blank=True, help_text="Numéro de la victime pour rappel"
    )
    photo = models.ImageField(upload_to="alertes/", null=True, blank=True, help_text="Photo de l'incident")
    gravite = models.CharField(
        max_length=2, choices=Gravite.choices, default=Gravite.P2,
        help_text="Niveau de gravité évalué par le régulateur"
    )
    statut = models.CharField(
        max_length=20, choices=StatutAlerte.choices, default=StatutAlerte.EN_ATTENTE
    )
    date_creation = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alerte {self.id_suivi} - {self.get_gravite_display()} - {self.date_creation:%d/%m/%Y %H:%M}"


class Mission(models.Model):
    """UC_03 / UC_04 - Envoyer une ambulance + Mettre à jour le statut."""

    class Statut(models.TextChoices):
        EN_ROUTE = "en_route", "En route"
        ARRIVE = "arrive", "Arrivé sur les lieux"
        PRISE_EN_CHARGE = "prise_en_charge", "Prise en charge"
        TRANSPORT = "transport", "Transport vers l'hôpital"
        TERMINE = "termine", "Terminé"
        EN_PANNE = "en_panne", "En panne"

    alerte = models.OneToOneField(Alerte, on_delete=models.CASCADE, related_name="mission")
    ambulance = models.ForeignKey(Ambulance, on_delete=models.PROTECT, related_name="missions")
    medecin_regulateur = models.ForeignKey(
        Utilisateur, on_delete=models.SET_NULL, null=True, related_name="missions_regulees"
    )
    hopital_recepteur = models.ForeignKey(
        Hopital, on_delete=models.SET_NULL, null=True, blank=True, related_name="missions"
    )
    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.EN_ROUTE)
    itineraire_optimise = models.JSONField(
        null=True, blank=True, help_text="Réponse brute de l'API de cartographie"
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_fin = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Mission {self.id} - {self.get_statut_display()}"
