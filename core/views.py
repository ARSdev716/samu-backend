from django.utils import timezone
from rest_framework import viewsets, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Ambulance, Alerte, Mission, Hopital, Utilisateur
from .serializers import (
    CustomTokenObtainPairSerializer,
    LoginMatriculeSerializer,
    AmbulanceSerializer,
    AlerteSerializer,
    SosSerializer,
    MissionSerializer,
    HopitalSerializer,
    EnvoyerAmbulanceSerializer,
    MettreAJourStatutSerializer,
)
from .permissions import (
    AccesSosPublic,
    EstAuthentifie,
    EstRegulateurOuAdmin,
    EstEquipeIntervention,
    LectureOuRegulateur,
)
from .services.itineraire import calculer_itineraire_optimal


# ──────────────────────────────────────────────
# UC_01 — Authentification & Inscription
# ──────────────────────────────────────────────

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Utilisateur
        fields = ["username", "password", "email", "telephone", "role"]

    def create(self, validated_data):
        # Par défaut, on force le rôle usager pour les inscriptions publiques
        # (seul un admin pourrait créer les autres rôles depuis l'interface admin)
        role = validated_data.get("role", Utilisateur.Role.USAGER)
        user = Utilisateur.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            email=validated_data.get("email", ""),
            telephone=validated_data.get("telephone", ""),
            role=role,
        )
        return user


class RegisterViewSet(viewsets.GenericViewSet):
    permission_classes = []
    serializer_class = RegisterSerializer

    @action(detail=False, methods=["post"])
    def creer(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        # On retourne directement un token pour connecter l'utilisateur
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role
        refresh["username"] = user.username
        
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "role": user.role
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def login_matricule(self, request):
        """Authentification ambulancier par matricule de l'ambulance."""
        serializer = LoginMatriculeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        matricule = serializer.validated_data["matricule"]
        password = serializer.validated_data["password"]
        
        try:
            ambulance = Ambulance.objects.get(matricule=matricule)
        except Ambulance.DoesNotExist:
            return Response({"detail": "Matricule introuvable."}, status=status.HTTP_404_NOT_FOUND)
        
        if not ambulance.ambulancier:
            return Response({"detail": "Aucun ambulancier assigné à ce véhicule."}, status=status.HTTP_400_BAD_REQUEST)
        
        user = ambulance.ambulancier
        if not user.check_password(password):
            return Response({"detail": "Mot de passe incorrect."}, status=status.HTTP_401_UNAUTHORIZED)
        
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        refresh["role"] = user.role
        refresh["username"] = user.username
        refresh["ambulance_id"] = ambulance.id
        refresh["matricule"] = ambulance.matricule
        
        return Response({
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "role": user.role,
            "ambulance_id": ambulance.id,
            "matricule": ambulance.matricule,
        })


class CustomTokenObtainPairView(TokenObtainPairView):
    """UC_01 - S'authentifier."""

    serializer_class = CustomTokenObtainPairSerializer


# ──────────────────────────────────────────────
# UC_02 — Déclenchement d'alerte (SOS public)
# ──────────────────────────────────────────────

class SosViewSet(viewsets.GenericViewSet):
    """
    UC_02 - Endpoint SOS accessible SANS authentification.
    """
    queryset = Alerte.objects.all()
    serializer_class = SosSerializer
    permission_classes = [AccesSosPublic]
    lookup_field = "id_suivi"

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usager = request.user if request.user.is_authenticated else None
        alerte = serializer.save(usager=usager)
        return Response(SosSerializer(alerte).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        """Permet à l'usager de consulter l'état de son alerte."""
        alerte = self.get_object()
        return Response(SosSerializer(alerte).data)

    @action(detail=True, methods=["post"])
    def annuler(self, request, id_suivi=None):
        """Permet à l'usager d'annuler son alerte si elle n'est pas déjà terminée."""
        alerte = self.get_object()
        if alerte.statut in [Alerte.StatutAlerte.EN_ATTENTE, Alerte.StatutAlerte.PRISE_EN_CHARGE]:
            alerte.statut = Alerte.StatutAlerte.ANNULEE
            alerte.save(update_fields=["statut"])
            return Response({"detail": "Alerte annulée avec succès."})
        return Response(
            {"detail": "Impossible d'annuler cette alerte à ce stade."},
            status=status.HTTP_400_BAD_REQUEST
        )

    from rest_framework.parsers import MultiPartParser, FormParser
    
    @action(detail=True, methods=["post"], parser_classes=[MultiPartParser, FormParser])
    def photo(self, request, id_suivi=None):
        """Permet d'ajouter une photo à une alerte."""
        alerte = self.get_object()
        
        # Log détaillé pour déboguer
        print("Fichiers reçus :", request.FILES)
        
        if 'photo' not in request.FILES:
            return Response({"detail": "Aucune photo fournie. Fichiers reçus : " + str(list(request.FILES.keys()))}, status=status.HTTP_400_BAD_REQUEST)
            
        alerte.photo = request.FILES['photo']
        alerte.save(update_fields=['photo'])
        return Response(SosSerializer(alerte).data)


class AlerteViewSet(viewsets.ModelViewSet):
    """UC_02 - Gestion complète des alertes (authentifié)."""

    queryset = Alerte.objects.all().order_by("-date_creation")
    serializer_class = AlerteSerializer
    permission_classes = [EstAuthentifie]

    def perform_create(self, serializer):
        # L'usager authentifié est automatiquement rattaché à son alerte.
        serializer.save(usager=self.request.user)


# ──────────────────────────────────────────────
# Hôpitaux — lecture seule
# ──────────────────────────────────────────────

class HopitalViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Hopital.objects.all()
    serializer_class = HopitalSerializer
    permission_classes = [EstAuthentifie]


# ──────────────────────────────────────────────
# Ambulances — lecture pour tous, écriture régulateur
# ──────────────────────────────────────────────

class AmbulanceViewSet(viewsets.ModelViewSet):
    """Consultation du parc + mise à jour de position (relayée en temps réel par Supabase)."""

    queryset = Ambulance.objects.all()
    serializer_class = AmbulanceSerializer
    permission_classes = [LectureOuRegulateur]

    @action(detail=True, methods=["post"], permission_classes=[EstEquipeIntervention])
    def position(self, request, pk=None):
        """Mise à jour de la position GPS par l'équipe terrain."""
        ambulance = self.get_object()
        lat = request.data.get("latitude")
        lon = request.data.get("longitude")
        if lat is None or lon is None:
            return Response(
                {"detail": "Latitude et longitude sont obligatoires."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        ambulance.latitude = float(lat)
        ambulance.longitude = float(lon)
        ambulance.derniere_maj_position = timezone.now()
        ambulance.save(update_fields=["latitude", "longitude", "derniere_maj_position"])
        # Supabase Realtime notifie l'app via la réplication logique.
        return Response(AmbulanceSerializer(ambulance).data)


# ──────────────────────────────────────────────
# UC_03 / UC_04 — Missions
# ──────────────────────────────────────────────

class MissionViewSet(viewsets.ModelViewSet):
    """UC_03 - Envoyer une ambulance / UC_04 - Mettre à jour le statut."""

    queryset = Mission.objects.select_related(
        "alerte", "ambulance", "medecin_regulateur", "hopital_recepteur"
    ).order_by("-date_creation")
    serializer_class = MissionSerializer
    permission_classes = [EstAuthentifie]

    @action(detail=False, methods=["post"], permission_classes=[EstRegulateurOuAdmin])
    def envoyer(self, request):
        """UC_03 : sélectionne une ambulance disponible et déclenche la mission."""
        payload = EnvoyerAmbulanceSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data

        try:
            alerte = Alerte.objects.get(pk=data["alerte_id"])
        except Alerte.DoesNotExist:
            return Response(
                {"detail": "Alerte introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            ambulance = Ambulance.objects.select_for_update().get(
                pk=data["ambulance_id"], statut=Ambulance.Statut.DISPONIBLE
            )
        except Ambulance.DoesNotExist:
            return Response(
                {"detail": "Ambulance introuvable ou non disponible."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        itineraire = calculer_itineraire_optimal(
            origine=(ambulance.latitude, ambulance.longitude),
            destination=(alerte.latitude, alerte.longitude),
        )

        mission = Mission.objects.create(
            alerte=alerte,
            ambulance=ambulance,
            medecin_regulateur=request.user,
            hopital_recepteur_id=data.get("hopital_id"),
            itineraire_optimise=itineraire,
        )
        ambulance.statut = Ambulance.Statut.EN_MISSION
        ambulance.save(update_fields=["statut"])

        # Marquer l'alerte comme prise en charge
        alerte.statut = Alerte.StatutAlerte.PRISE_EN_CHARGE
        alerte.save(update_fields=["statut"])

        return Response(MissionSerializer(mission).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], permission_classes=[EstEquipeIntervention])
    def ma_mission(self, request):
        """Retourne la mission active de l'ambulancier connecté."""
        # Trouver l'ambulance assignée à cet ambulancier
        ambulance = Ambulance.objects.filter(ambulancier=request.user).first()
        if not ambulance:
            return Response({"detail": "Aucune ambulance assignée."}, status=status.HTTP_404_NOT_FOUND)
        
        mission = Mission.objects.filter(
            ambulance=ambulance
        ).exclude(
            statut=Mission.Statut.TERMINE
        ).select_related(
            "alerte", "ambulance", "medecin_regulateur", "hopital_recepteur"
        ).order_by("-date_creation").first()
        
        if not mission:
            return Response({"detail": "Aucune mission active."}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(MissionSerializer(mission).data)

    @action(detail=True, methods=["post"], permission_classes=[EstEquipeIntervention])
    def statut(self, request, pk=None):
        """UC_04 : fait avancer le statut d'une mission et libère l'ambulance si terminée."""
        mission = self.get_object()
        payload = MettreAJourStatutSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        nouveau_statut = payload.validated_data["statut"]

        mission.statut = nouveau_statut
        if nouveau_statut == Mission.Statut.TERMINE:
            mission.date_fin = timezone.now()
            mission.ambulance.statut = Ambulance.Statut.DISPONIBLE
            mission.ambulance.save(update_fields=["statut"])
        elif nouveau_statut == "en_panne":
            mission.ambulance.statut = Ambulance.Statut.EN_PANNE
            mission.ambulance.save(update_fields=["statut"])
        mission.save()

        return Response(MissionSerializer(mission).data)
# ==========================================
# Tableau de Bord (Web MVP)
# ==========================================
from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny

def dashboard_view(request):
    return render(request, 'core/dashboard.html')

@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def dashboard_data(request):
    alertes_en_cours = Alerte.objects.exclude(statut='annulee').exclude(mission__statut='termine').order_by('-date_creation')
    ambulances = Ambulance.objects.all()
    missions = Mission.objects.all().order_by('-date_creation')
    hopitaux = Hopital.objects.all()
    
    return Response({
        'alertes': AlerteSerializer(alertes_en_cours, many=True, context={'request': request}).data,
        'ambulances': AmbulanceSerializer(ambulances, many=True).data,
        'missions': MissionSerializer(missions, many=True).data,
        'hopitaux': HopitalSerializer(hopitaux, many=True).data,
    })

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def dashboard_assign(request):
    alerte_id = request.data.get('alerte')
    ambulance_id = request.data.get('ambulance')
    
    try:
        alerte = Alerte.objects.get(id=alerte_id)
        ambulance = Ambulance.objects.get(id=ambulance_id)
        regulateur = Utilisateur.objects.filter(role='regulateur').first()
        if not regulateur:
            regulateur = Utilisateur.objects.first()
            
        mission = Mission.objects.create(
            alerte=alerte,
            ambulance=ambulance,
            medecin_regulateur=regulateur,
            instructions="Assignation rapide (Dashboard)"
        )
        
        ambulance.statut = Ambulance.Statut.EN_INTERVENTION
        ambulance.save(update_fields=['statut'])
        
        alerte.statut = Alerte.Statut.EN_COURS
        alerte.save(update_fields=['statut'])
        
        return Response({'success': True, 'mission': mission.id})
    except Exception as e:
        return Response({'error': str(e)}, status=400)
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def dashboard_update_alerte(request, pk):
    try:
        alerte = Alerte.objects.get(pk=pk)
        alerte.telephone_victime = request.data.get('telephone_victime', alerte.telephone_victime)
        alerte.description = request.data.get('description', alerte.description)
        alerte.gravite = request.data.get('gravite', alerte.gravite)
        alerte.save()
        return Response({'status': 'ok'})
    except Alerte.DoesNotExist:
        return Response({'error': 'Alerte introuvable'}, status=404)

@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def dashboard_update_mission(request, pk):
    try:
        mission = Mission.objects.get(pk=pk)
        mission.statut = request.data.get('statut', mission.statut)
        mission.save()
        
        # Si la mission est terminee, on libere l'ambulance et l'alerte
        if mission.statut == 'termine':
            mission.ambulance.statut = 'disponible'
            mission.ambulance.save()
            mission.alerte.statut = 'termine'
            mission.alerte.save()
            
        return Response({'status': 'ok'})
    except Mission.DoesNotExist:
        return Response({'error': 'Mission introuvable'}, status=404)
