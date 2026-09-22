"""
Calcul de l'itinéraire optimal entre une ambulance et le lieu d'une alerte.

Utilise OSRM (Open Source Routing Machine, gratuit, pas de clé API) par défaut.
Pour passer sur Google Maps Directions API, remplacer le contenu de
`_appeler_osrm` par un appel à `https://maps.googleapis.com/maps/api/directions/json`.

Le scénario d'exception 11a du cas "Envoyer Ambulance" (API de géolocalisation
indisponible) est couvert par le repli `_itineraire_direct`.
"""

import requests

OSRM_BASE_URL = "https://router.project-osrm.org/route/v1/driving"
TIMEOUT_SECONDES = 5


def calculer_itineraire_optimal(origine, destination):
    """
    origine / destination : tuples (latitude, longitude)
    Retourne un dict JSON-sérialisable stocké dans Mission.itineraire_optimise.
    """
    if None in origine or None in destination:
        return _itineraire_direct(origine, destination, motif="coordonnees_incompletes")

    try:
        return _appeler_osrm(origine, destination)
    except (requests.RequestException, ValueError):
        # 11a : on retombe sur un itinéraire par coordonnées directes.
        return _itineraire_direct(origine, destination, motif="api_indisponible")


def _appeler_osrm(origine, destination):
    lat1, lon1 = origine
    lat2, lon2 = destination
    url = f"{OSRM_BASE_URL}/{lon1},{lat1};{lon2},{lat2}"
    reponse = requests.get(url, params={"overview": "full", "geometries": "geojson"}, timeout=TIMEOUT_SECONDES)
    reponse.raise_for_status()
    donnees = reponse.json()
    if donnees.get("code") != "Ok":
        raise ValueError("Réponse OSRM invalide")

    trajet = donnees["routes"][0]
    return {
        "source": "osrm",
        "distance_metres": trajet["distance"],
        "duree_secondes": trajet["duration"],
        "geometrie": trajet["geometry"],
    }


def _itineraire_direct(origine, destination, motif):
    return {
        "source": "repli_direct",
        "motif": motif,
        "origine": origine,
        "destination": destination,
    }
