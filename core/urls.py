from rest_framework.routers import DefaultRouter
from .views import AlerteViewSet, AmbulanceViewSet, MissionViewSet, HopitalViewSet, SosViewSet, RegisterViewSet

router = DefaultRouter()
router.register("alertes", AlerteViewSet, basename="alerte")
router.register("ambulances", AmbulanceViewSet, basename="ambulance")
router.register("missions", MissionViewSet, basename="mission")
router.register("hopitaux", HopitalViewSet, basename="hopital")
router.register("auth", RegisterViewSet, basename="auth")

# UC_02 - Endpoint SOS public (POST /api/sos/)
router.register("sos", SosViewSet, basename="sos")

urlpatterns = router.urls
from django.urls import path
from . import views

urlpatterns += [
    path('dashboard_data/', views.dashboard_data, name='dashboard_data'),
    path('missions/envoyer_dashboard/', views.dashboard_assign, name='dashboard_assign'),
    path('dashboard/alerte/<int:pk>/', views.dashboard_update_alerte, name='dashboard_update_alerte'),
    path('dashboard/mission/<int:pk>/', views.dashboard_update_mission, name='dashboard_update_mission'),
]
