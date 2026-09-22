from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Utilisateur, Ambulance, Hopital, Alerte
from core.services.itineraire import calculer_itineraire_optimal

class ARSTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = Utilisateur.objects.create_user(
            username="testuser",
            password="testpassword123",
            role=Utilisateur.Role.MEDECIN_REGULATEUR,
        )
        self.ambulance = Ambulance.objects.create(
            matricule="AMB-TEST-01",
            statut=Ambulance.Statut.DISPONIBLE,
            latitude=4.05,
            longitude=9.71,
        )
        self.hopital = Hopital.objects.create(
            nom="Hôpital Test",
            latitude=4.06,
            longitude=9.72,
        )

    def test_authentification_jwt(self):
        url = reverse("token_obtain_pair")
        response = self.client.post(url, {
            "username": "testuser",
            "password": "testpassword123"
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_liste_ambulances_authentifie(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get("/api/ambulances/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["matricule"], "AMB-TEST-01")

    def test_creation_alerte(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post("/api/alertes/", {
            "latitude": 4.052,
            "longitude": 9.715,
            "description": "Accident grave",
            "adresse_manuelle": "Rue des tests",
        }, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Alerte.objects.count(), 1)

    def test_calcul_itineraire_repli(self):
        # Test itineraire direct en cas de coordonnées incomplètes
        res = calculer_itineraire_optimal((None, None), (4.05, 9.71))
        self.assertEqual(res["source"], "repli_direct")
        self.assertEqual(res["motif"], "coordonnees_incompletes")
