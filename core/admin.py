from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Utilisateur, Ambulance, Alerte, Mission, Hopital


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Rôle ARS", {"fields": ("role", "telephone")}),)
    list_display = ("username", "role", "telephone", "is_staff")


admin.site.register(Ambulance)
admin.site.register(Alerte)
admin.site.register(Mission)
admin.site.register(Hopital)
