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

    def validate(self, attrs):
        data = super().validate(attrs)
        data["role"] = self.user.role
        data["username"] = self.user.username
        return data


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
    mission_statut = serializers.SerializerMethodField()
    ambulance_matricule = serializers.SerializerMethodField()

    class Meta:
        model = Alerte
        fields = [
            "id", "id_suivi", "usager", "latitude", "longitude",
            "adresse_manuelle", "description", "telephone_victime",
            "gravite", "statut", "date_creation", "photo",
            "mission_statut", "ambulance_matricule",
        ]
        read_only_fields = ["id", "id_suivi", "usager", "statut", "date_creation"]

    def get_mission_statut(self, obj):
        if hasattr(obj, 'mission') and obj.mission:
            return obj.mission.statut
        return None

    def get_ambulance_matricule(self, obj):
        if hasattr(obj, 'mission') and obj.mission and obj.mission.ambulance:
            return obj.mission.ambulance.matricule
        return None


class SosSerializer(serializers.ModelSerializer):
    """
    UC_02 - Endpoint SOS public (sans authentification).
    Fournit la position en temps réel de l'ambulance et l'itinéraire tracé.
    """
    ambulance_latitude = serializers.SerializerMethodField()
    ambulance_longitude = serializers.SerializerMethodField()
    ambulance_matricule = serializers.SerializerMethodField()
    mission_statut = serializers.SerializerMethodField()
    itineraire_points = serializers.SerializerMethodField()

    class Meta:
        model = Alerte
        fields = [
            "id", "id_suivi", "latitude", "longitude",
            "adresse_manuelle", "description", "telephone_victime",
            "statut", "date_creation", "photo",
            "ambulance_latitude", "ambulance_longitude",
            "ambulance_matricule", "mission_statut", "itineraire_points",
        ]
        read_only_fields = ["id", "id_suivi", "statut", "date_creation"]

    def get_ambulance_latitude(self, obj):
        if hasattr(obj, "mission") and obj.mission and obj.mission.ambulance:
            return obj.mission.ambulance.latitude
        return None

    def get_ambulance_longitude(self, obj):
        if hasattr(obj, "mission") and obj.mission and obj.mission.ambulance:
            return obj.mission.ambulance.longitude
        return None

    def get_ambulance_matricule(self, obj):
        if hasattr(obj, "mission") and obj.mission and obj.mission.ambulance:
            return obj.mission.ambulance.matricule
        return None

    def get_mission_statut(self, obj):
        if hasattr(obj, "mission") and obj.mission:
            return obj.mission.statut
        return None

    def get_itineraire_points(self, obj):
        if not hasattr(obj, "mission") or not obj.mission:
            return []
        mission = obj.mission
        iti = mission.itineraire_optimise
        if iti and isinstance(iti, dict):
            geometrie = iti.get("geometrie", {})
            coords = geometrie.get("coordinates", [])
            if coords:
                return [{"latitude": c[1], "longitude": c[0]} for c in coords]
            if "origine" in iti and "destination" in iti and iti["origine"] and iti["destination"]:
                return [
                    {"latitude": iti["origine"][0], "longitude": iti["origine"][1]},
                    {"latitude": iti["destination"][0], "longitude": iti["destination"][1]},
                ]
        # Repli direct : position ambulance -> position alerte
        if (
            mission.ambulance
            and mission.ambulance.latitude
            and mission.ambulance.longitude
            and obj.latitude
            and obj.longitude
        ):
            return [
                {"latitude": mission.ambulance.latitude, "longitude": mission.ambulance.longitude},
                {"latitude": obj.latitude, "longitude": obj.longitude},
            ]
        return []


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
        if iti and isinstance(iti, dict):
            geometrie = iti.get("geometrie", {})
            coords = geometrie.get("coordinates", [])
            if coords:
                return [{"latitude": c[1], "longitude": c[0]} for c in coords]
            if "origine" in iti and "destination" in iti and iti["origine"] and iti["destination"]:
                return [
                    {"latitude": iti["origine"][0], "longitude": iti["origine"][1]},
                    {"latitude": iti["destination"][0], "longitude": iti["destination"][1]},
                ]
        # Repli direct
        if (
            obj.ambulance
            and obj.ambulance.latitude
            and obj.ambulance.longitude
            and obj.alerte
            and obj.alerte.latitude
            and obj.alerte.longitude
        ):
            return [
                {"latitude": obj.ambulance.latitude, "longitude": obj.ambulance.longitude},
                {"latitude": obj.alerte.latitude, "longitude": obj.alerte.longitude},
            ]
        return []


class EnvoyerAmbulanceSerializer(serializers.Serializer):
    """UC_03 - payload minimal pour déclencher une mission depuis une alerte."""

    alerte_id = serializers.IntegerField()
    ambulance_id = serializers.IntegerField()
    hopital_id = serializers.IntegerField(required=False)


class MettreAJourStatutSerializer(serializers.Serializer):
    """UC_04"""

    statut = serializers.ChoiceField(choices=Mission.Statut.choices)
