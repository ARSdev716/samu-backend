from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Utilisateur, Ambulance, Alerte, Mission, Hopital


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """UC_01 - ajoute le rôle dans le token pour que l'app affiche le bon espace de travail."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["username"] = user.username
        return token


class LoginMatriculeSerializer(serializers.Serializer):
    """Authentification ambulancier par matricule."""
    matricule = serializers.CharField()
    password = serializers.CharField(write_only=True)


class AmbulanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ambulance
        fields = [
            "id", "matricule", "equipement", "statut",
            "latitude", "longitude", "derniere_maj_position",
        ]
        read_only_fields = ["id", "derniere_maj_position"]


class HopitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hopital
        fields = ["id", "nom", "latitude", "longitude", "capacite_lits", "telephone"]


class AlerteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alerte
        fields = [
            "id", "id_suivi", "usager", "latitude", "longitude",
            "adresse_manuelle", "description", "telephone_victime",
            "gravite", "statut", "date_creation", "photo"
        ]
        read_only_fields = ["id", "id_suivi", "usager", "statut", "date_creation"]


class SosSerializer(serializers.ModelSerializer):
    """
    UC_02 - Endpoint SOS public (sans authentification).
    """
    ambulance_latitude = serializers.SerializerMethodField()
    ambulance_longitude = serializers.SerializerMethodField()
    mission_statut = serializers.SerializerMethodField()

    class Meta:
        model = Alerte
        fields = [
            "id", "id_suivi", "latitude", "longitude",
            "adresse_manuelle", "description", "telephone_victime",
            "statut", "date_creation", "ambulance_latitude", "ambulance_longitude", "photo", "mission_statut"
        ]
        read_only_fields = ["id", "id_suivi", "statut", "date_creation"]
        
    def get_ambulance_latitude(self, obj):
        if hasattr(obj, 'mission') and obj.mission and obj.mission.ambulance:
            return obj.mission.ambulance.latitude
        return None
        
    def get_ambulance_longitude(self, obj):
        if hasattr(obj, 'mission') and obj.mission and obj.mission.ambulance:
            return obj.mission.ambulance.longitude
        return None

    def get_mission_statut(self, obj):
        if hasattr(obj, 'mission') and obj.mission:
            return obj.mission.statut
        return None


class MissionSerializer(serializers.ModelSerializer):
    ambulance_detail = AmbulanceSerializer(source="ambulance", read_only=True)
    alerte_detail = AlerteSerializer(source="alerte", read_only=True)
    hopital_detail = HopitalSerializer(source="hopital_recepteur", read_only=True)
    itineraire_points = serializers.SerializerMethodField()

    class Meta:
        model = Mission
        fields = [
            "id", "alerte", "ambulance", "medecin_regulateur",
            "hopital_recepteur", "statut", "itineraire_optimise",
            "date_creation", "date_fin",
            "ambulance_detail", "alerte_detail",
            "hopital_detail", "itineraire_points",
        ]
        read_only_fields = ["id", "date_creation", "date_fin", "itineraire_optimise"]

    def get_itineraire_points(self, obj):
        """Extrait les coordonnées de l'itinéraire OSRM pour la carte mobile."""
        iti = obj.itineraire_optimise
        if not iti:
            return []
        # OSRM retourne la géométrie en GeoJSON
        geometrie = iti.get("geometrie", {})
        coords = geometrie.get("coordinates", [])
        # GeoJSON = [lng, lat], on convertit en {latitude, longitude}
        return [{"latitude": c[1], "longitude": c[0]} for c in coords]


class EnvoyerAmbulanceSerializer(serializers.Serializer):
    """UC_03 - payload minimal pour déclencher une mission depuis une alerte."""

    alerte_id = serializers.IntegerField()
    ambulance_id = serializers.IntegerField()
    hopital_id = serializers.IntegerField(required=False)


class MettreAJourStatutSerializer(serializers.Serializer):
    """UC_04"""

    statut = serializers.ChoiceField(choices=Mission.Statut.choices)
