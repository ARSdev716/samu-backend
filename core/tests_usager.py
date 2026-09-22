from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from core.models import Utilisateur, Alerte

class UsagerTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        # UC_Usager_1: Inscription
        self.usager = Utilisateur.objects.create_user(
            username="patient_test",
            password="password123",
            role=Utilisateur.Role.USAGER,
            telephone="690000000"
        )
        # Auth token
        response = self.client.post(reverse("token_obtain_pair"), {
            "username": "patient_test",
            "password": "password123"
        }, format="json")
        self.token = response.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + self.token)

    def test_uc_1_authentification(self):
        """Test UC: S'authentifier"""
        self.assertEqual(self.usager.role, Utilisateur.Role.USAGER)
        self.assertIsNotNone(self.token)

    def test_uc_3_signaler_urgence(self):
        """Test UC: Signaler une urgence (SOS)"""
        payload = {
            "latitude": 4.051,
            "longitude": 9.712,
            "description": "Douleur thoracique",
            "adresse_manuelle": "Quartier Bonamoussadi"
        }
        response = self.client.post("/api/alertes/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Alerte.objects.count(), 1)
        alerte = Alerte.objects.first()
        # Vérifier lien usager
        self.assertEqual(alerte.usager, self.usager)
        self.assertEqual(alerte.statut, 'en_attente')

    def test_uc_4_suivre_intervention(self):
        """Test UC: Suivre Intervention"""
        # Créer une alerte
        alerte = Alerte.objects.create(
            usager=self.usager,
            latitude=4.051,
            longitude=9.712,
            statut='en_attente'
        )
        response = self.client.get(f"/api/alertes/{alerte.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["statut"], "en_attente")
