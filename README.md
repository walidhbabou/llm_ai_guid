# Backend IA Guide Touristique (Python)

Backend modulaire en FastAPI qui:
- analyse une requete utilisateur avec un LLM,
- appelle Google Maps Places + Geocoding,
- retourne un JSON propre et standardise,
- peut aussi generer une reponse guide dans `assistant_reply`,
- propose une interface `/ui` ou l'utilisateur peut poser sa question en texte ou en audio et ecouter la reponse.

## Architecture

```text
app/
  api/routes/ai_search.py         # Route REST
  controllers/search_controller.py
  services/search_service.py      # Orchestration du flux
  services/response_formatter.py
  llm/analyzer.py                 # Analyse requete (LLM + fallback)
  llm/assistant.py                # Reponse guide conversationnelle
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
- `GROQ_API_KEY` (optionnel, fallback heuristique si absent)
- `GEMINI_API_KEY` (optionnel, pour la génération narrative Gemini Flash)
- `GROQ_MODEL`
- `GEMINI_MODEL` (optionnel, défaut `gemini-2.0-flash`)
- `GROQ_SPEECH_MODEL` (optionnel, utilise Groq Speech-to-Text si defini)
- `LOCAL_WHISPER_MODEL` / `LOCAL_WHISPER_DEVICE` / `LOCAL_WHISPER_COMPUTE_TYPE`
  (optionnel, transcription locale Whisper sans cle)

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
  - `GROQ_API_KEY` (optionnel si vous acceptez le fallback heuristique)

Render va:
- installer `requirements.txt`
- lancer `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- verifier la sante sur `/health`

Variables disponibles dans `.env.example`:
- `GROQ_MODEL`
- `GOOGLE_SEARCH_RADIUS_METERS`
- `GOOGLE_NEAR_ME_RADIUS_METERS`
- `GOOGLE_LANGUAGE`
- `GOOGLE_REGION`

Notes:
- Si la carte n'apparait pas sur `/ui`, verifier que `GOOGLE_MAPS_API_KEY` est bien defini.
- Si vous voyez `ApiNotActivatedMapError`, ce n'est pas un bug du code: dans Google Cloud, activez `Maps JavaScript API` pour le projet de la cle, puis verifiez que le billing est actif et que les restrictions HTTP referrer incluent votre domaine ou `http://localhost:*`.
- Gardez une seule valeur `GOOGLE_MAPS_API_KEY` dans `.env`. Si plusieurs lignes existent, la derniere gagne et peut pointer vers un autre projet Google Cloud.
- `GEMINI_API_KEY` sert au LLM, pas a Google Maps. Elle permet d'utiliser Gemini pour les reponses narratives (itineraire, description, FAQ) quand elle est presente.
- Si vous voyez une erreur 500 au boot, verifier les logs Render et les variables d'environnement.

## Utiliser Gemini au lieu de Groq pour les reponses narratives

1. Ajouter dans `.env`:

```env
GEMINI_API_KEY=votre_cle_gemini
GEMINI_MODEL=gemini-2.0-flash
```

2. Redemarrer le serveur.
3. Les requetes d'itineraire utiliseront Gemini Flash pour la partie narrative, avec Groq conserve pour l'analyse d'intention et le fallback.

## Endpoint principal

- `POST /api/ai/search`
- `POST /api/ai/search/audio`
- Interface de test web: `GET /ui`

## Mode audio dans l'interface `/ui`

L'endpoint backend reste en JSON texte, mais l'interface web ajoute deux fonctions cote navigateur:
- question par texte ou saisie vocale avec le micro,
- reponse affichee en texte et lecture audio optionnelle,
- envoi d'un vrai fichier audio au backend via `multipart/form-data`.

Details utiles:
- la saisie vocale repose sur l'API Web Speech du navigateur,
- la lecture audio repose sur `speechSynthesis`,
- l'endpoint audio backend utilise Groq Speech-to-Text si la cle est presente,
  sinon la transcription locale Whisper est utilisee,
- pour le meilleur support micro, utilisez de preference Chrome ou Edge,
- si le navigateur ne supporte pas l'audio, l'interface continue de fonctionner en mode texte.

Exemple d'appel backend audio:

```bash
curl -X POST http://127.0.0.1:8000/api/ai/search/audio \
  -F "audio=@question.webm" \
  -F "language=fr" \
  -F "user_latitude=33.5731" \
  -F "user_longitude=-7.5898"
```

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
  "assistant_reply": "J'ai trouve 2 cafes a Rabat. Les premiers choix sont Cafe Exemple et Cafe Medina.",
  "results": [
    {
      "name": "Cafe Exemple",
      "address": "Avenue Mohammed V, Rabat",
      "latitude": 34.0209,
      "longitude": -6.8416,
      "rating": 4.5,
      "types": ["cafe", "food", "point_of_interest"],
      "photo_url": "https://maps.googleapis.com/maps/api/place/photo?...",
      "photo_urls": [
        "https://maps.googleapis.com/maps/api/place/photo?...",
        "https://maps.googleapis.com/maps/api/place/photo?..."
      ],
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

- Le LLM n'invente pas de lieux: il sert a parser la requete et a rediger `assistant_reply`.
- Le backend peut aussi repondre a certaines questions generales de guide touristique via `assistant_reply`.
- Les lieux proviennent exclusivement de Google Maps API.
- Si aucune ville n'est detectee et des coordonnees utilisateur sont fournies, le backend tente une deduction via reverse geocoding.
- Les erreurs Google/LLM sont retournees en JSON propre.
# llm_ai_guid
