# Backend IA Guide Touristique (Python)

Backend modulaire en FastAPI qui:
- analyse une requete utilisateur avec un LLM,
- appelle Google Maps Places + Geocoding,
- retourne un JSON propre et standardise.

## Architecture

```text
app/
  api/routes/ai_search.py         # Route REST
  controllers/search_controller.py
  services/search_service.py      # Orchestration du flux
  services/response_formatter.py
  llm/analyzer.py                 # Analyse requete (LLM + fallback)
  llm/system_prompt.py            # Prompt systeme
  clients/google_maps_client.py   # Appels Google APIs
  dto/search_dto.py               # Request/Response DTOs
  mappers/place_mapper.py         # Mapping Google -> DTO
  core/config.py                  # Variables d'environnement
  core/exceptions.py
  main.py
```

## Installation

1. Creer un environnement virtuel.
2. Installer les dependances:

```bash
pip install -r requirements.txt
```

3. Copier `.env.example` en `.env` et renseigner:
- `GOOGLE_MAPS_API_KEY`
- `OPENAI_API_KEY` (optionnel, fallback heuristique si absent)
- `OPENAI_MODEL`

## Lancer le serveur

```bash
uvicorn app.main:app --reload
```

## Deploiement sur Render

Ce repo contient deja `render.yaml` pour un deploiement automatique.

1. Pousser le code sur GitHub.
2. Sur Render: New + Blueprint.
3. Selectionner le repository.
4. Valider le service detecte dans `render.yaml`.
5. Ajouter les secrets obligatoires dans Render:
  - `GOOGLE_MAPS_API_KEY`
  - `OPENAI_API_KEY` (optionnel si vous acceptez le fallback heuristique)

Render va:
- installer `requirements.txt`
- lancer `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- verifier la sante sur `/health`

Variables disponibles dans `.env.example`:
- `OPENAI_MODEL`
- `GOOGLE_SEARCH_RADIUS_METERS`
- `GOOGLE_NEAR_ME_RADIUS_METERS`
- `GOOGLE_LANGUAGE`
- `GOOGLE_REGION`

Notes:
- Si la carte n'apparait pas sur `/ui`, verifier que `GOOGLE_MAPS_API_KEY` est bien defini.
- Si vous voyez une erreur 500 au boot, verifier les logs Render et les variables d'environnement.

## Endpoint principal

- `POST /api/ai/search`
- Interface de test web: `GET /ui`

Exemple body:

```json
{
  "query": "Donne-moi les meilleurs cafes a Rabat"
}
```

Avec geolocalisation (utile pour "proches de moi"):

```json
{
  "query": "Trouve-moi des restaurants proches de moi",
  "user_latitude": 33.5731,
  "user_longitude": -7.5898
}
```

## Exemple de reponse JSON

```json
{
  "intent": "search_places",
  "city": "Rabat",
  "category": "cafe",
  "preferences": ["meilleurs"],
  "result_limit": 10,
  "near_me": false,
  "results_count": 2,
  "results": [
    {
      "name": "Cafe Exemple",
      "address": "Avenue Mohammed V, Rabat",
      "latitude": 34.0209,
      "longitude": -6.8416,
      "rating": 4.5,
      "types": ["cafe", "food", "point_of_interest"],
      "photo_url": "https://maps.googleapis.com/maps/api/place/photo?...",
      "place_id": "ChIJxxxx",
      "google_maps_url": "https://www.google.com/maps/place/?q=place_id:ChIJxxxx"
    }
  ],
  "message": null
}
```

## Prompt systeme LLM (extrait)

Le prompt est dans `app/llm/system_prompt.py` et force un JSON structure avec:
- intent
- city
- category
- preferences
- result_limit
- near_me

## Notes techniques

- Le LLM n'invente pas de lieux: il sert uniquement a parser la requete.
- Les lieux proviennent exclusivement de Google Maps API.
- Si aucune ville n'est detectee et des coordonnees utilisateur sont fournies, le backend tente une deduction via reverse geocoding.
- Les erreurs Google/LLM sont retournees en JSON propre.
# llm_ai_guid
