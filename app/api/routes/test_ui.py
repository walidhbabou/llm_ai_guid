from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.core.config import settings

router = APIRouter(tags=["test-ui"])


@router.get("/ui", response_class=HTMLResponse)
async def api_test_ui() -> str:
    google_maps_key = settings.google_maps_api_key.strip()
    google_maps_script = (
        "<script async defer src=\"https://maps.googleapis.com/maps/api/js?key="
        f"{google_maps_key}&libraries=places&callback=initGoogleMap\"></script>"
        if google_maps_key
        else ""
    )

    return (
        """
<!doctype html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>AI Tourist API Tester</title>
  <style>
    :root {
      --bg: #f5f2ea;
      --card: #fffdf8;
      --text: #1a1a1a;
      --muted: #5b5b5b;
      --line: #ded4c3;
      --accent: #005f73;
      --accent-2: #e76f51;
      --ok: #2a9d8f;
      --error: #b00020;
      --shadow: 0 12px 40px rgba(0, 0, 0, 0.08);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: "Segoe UI", "Trebuchet MS", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at 10% 0%, #fff8ea 0%, transparent 45%),
        radial-gradient(circle at 90% 15%, #dceef2 0%, transparent 40%),
        var(--bg);
      min-height: 100vh;
    }

    .container {
      width: min(1080px, 92vw);
      margin: 40px auto;
      display: grid;
      grid-template-columns: 340px 1fr;
      gap: 24px;
    }

    .panel {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: var(--shadow);
      padding: 18px;
      animation: rise 0.45s ease-out;
    }

    .title {
      margin: 0 0 8px;
      font-size: 26px;
      letter-spacing: 0.2px;
    }

    .subtitle {
      margin: 0 0 18px;
      color: var(--muted);
      font-size: 14px;
      line-height: 1.4;
    }

    label {
      display: block;
      font-size: 13px;
      margin-bottom: 6px;
      color: var(--muted);
    }

    input, textarea {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      padding: 10px 12px;
      font-size: 14px;
      margin-bottom: 12px;
      outline: none;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }

    textarea {
      min-height: 110px;
      resize: vertical;
      line-height: 1.35;
    }

    input:focus, textarea:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 4px rgba(0, 95, 115, 0.12);
    }

    .row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
    }

    .actions {
      display: flex;
      gap: 10px;
      margin-top: 4px;
      flex-wrap: wrap;
    }

    button {
      border: 0;
      border-radius: 999px;
      padding: 10px 16px;
      font-size: 14px;
      cursor: pointer;
      transition: transform 0.1s ease, opacity 0.2s ease;
    }

    .primary {
      background: var(--accent);
      color: #fff;
    }

    .secondary {
      background: #ebf5f7;
      color: var(--accent);
      border: 1px solid #c8e1e8;
    }

    button:hover { opacity: 0.95; }
    button:active { transform: translateY(1px); }
    button:disabled { opacity: 0.65; cursor: not-allowed; }

    .status {
      margin-top: 12px;
      min-height: 20px;
      font-size: 13px;
      color: var(--muted);
    }

    .status.ok { color: var(--ok); }
    .status.error { color: var(--error); }

    .head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 8px;
      margin-bottom: 12px;
    }

    .chip {
      border-radius: 999px;
      font-size: 12px;
      padding: 5px 10px;
      background: #f0ece1;
      border: 1px solid #e5dccb;
      color: #5a503c;
    }

    .summary {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }

    .metric {
      background: #fff;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px;
    }

    .metric small {
      display: block;
      color: var(--muted);
      margin-bottom: 5px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.6px;
    }

    .metric strong {
      font-size: 14px;
      word-break: break-word;
    }

    .cards {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
      gap: 12px;
      margin-bottom: 12px;
    }

    .place {
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 14px;
      padding: 12px;
      animation: rise 0.35s ease-out;
    }

    .place h4 {
      margin: 0 0 6px;
      font-size: 15px;
      line-height: 1.2;
    }

    .place p {
      margin: 0 0 8px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
      min-height: 32px;
    }

    .meta {
      display: flex;
      justify-content: space-between;
      gap: 6px;
      font-size: 12px;
      color: #574f3e;
      margin-bottom: 8px;
    }

    .links a {
      color: var(--accent-2);
      text-decoration: none;
      font-size: 12px;
      font-weight: 600;
    }

    .map-shell {
      border: 1px solid var(--line);
      border-radius: 14px;
      overflow: hidden;
      background: #fff;
      margin-bottom: 12px;
    }

    #map {
      width: 100%;
      height: 300px;
    }

    .map-note {
      font-size: 12px;
      color: var(--muted);
      margin: 8px 0 12px;
    }

    .json {
      border: 1px solid var(--line);
      border-radius: 12px;
      background: #fff;
      padding: 12px;
      white-space: pre-wrap;
      font-family: Consolas, "Courier New", monospace;
      font-size: 12px;
      max-height: 320px;
      overflow: auto;
    }

    @keyframes rise {
      from { transform: translateY(8px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }

    @media (max-width: 930px) {
      .container {
        grid-template-columns: 1fr;
        margin: 20px auto;
      }

      .summary {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }
  </style>
</head>
<body>
  <main class="container">
    <section class="panel">
      <h1 class="title">Testeur API IA</h1>
      <p class="subtitle">Envoie une requete vers <code>/api/ai/search</code> et verifie l'analyse IA ainsi que les lieux Google Maps.</p>

      <label for="query">Requete utilisateur</label>
      <textarea id="query">Donne-moi les meilleurs cafes pres de moi</textarea>

      <div class="row">
        <div>
          <label for="lat">Latitude (auto ou manuel)</label>
          <input id="lat" type="number" step="any" placeholder="33.5731" />
        </div>
        <div>
          <label for="lng">Longitude (auto ou manuel)</label>
          <input id="lng" type="number" step="any" placeholder="-7.5898" />
        </div>
      </div>

      <div class="actions">
        <button class="primary" id="btn-send">Lancer le test</button>
        <button class="secondary" id="btn-locate" type="button">Utiliser ma position</button>
        <button class="secondary" id="btn-clear" type="button">Vider</button>
      </div>

      <div id="status" class="status"></div>
    </section>

    <section class="panel">
      <div class="head">
        <h2 style="margin:0;font-size:19px;">Resultats</h2>
        <span class="chip" id="api-badge">POST /api/ai/search</span>
      </div>

      <div class="summary" id="summary">
        <div class="metric"><small>Intent</small><strong id="intent">-</strong></div>
        <div class="metric"><small>Ville</small><strong id="city">-</strong></div>
        <div class="metric"><small>Categorie</small><strong id="category">-</strong></div>
        <div class="metric"><small>Near Me</small><strong id="nearMe">-</strong></div>
      </div>

      <div class="cards" id="cards"></div>

      <div class="map-shell">
        <div id="map"></div>
      </div>
      <p class="map-note" id="map-note">Carte en attente des resultats...</p>

      <h3 style="margin:10px 0 8px;font-size:14px;color:#504831;">JSON brut</h3>
      <pre class="json" id="json-output">Aucune reponse pour le moment.</pre>
    </section>
  </main>

  __GOOGLE_MAPS_SCRIPT__
  <script>
    const googleMapsKey = "__GOOGLE_MAPS_KEY__";
    const queryInput = document.getElementById("query");
    const latInput = document.getElementById("lat");
    const lngInput = document.getElementById("lng");
    const btnSend = document.getElementById("btn-send");
    const btnLocate = document.getElementById("btn-locate");
    const btnClear = document.getElementById("btn-clear");
    const statusEl = document.getElementById("status");

    const intentEl = document.getElementById("intent");
    const cityEl = document.getElementById("city");
    const categoryEl = document.getElementById("category");
    const nearMeEl = document.getElementById("nearMe");
    const cardsEl = document.getElementById("cards");
    const jsonOutputEl = document.getElementById("json-output");
    const mapNoteEl = document.getElementById("map-note");

    let map = null;

    let resultMarkers = [];
    let userMarker = null;

    function initGoogleMap() {
      if (!googleMapsKey || !window.google || !window.google.maps) {
        mapNoteEl.textContent = "Google Maps non disponible (verifiez GOOGLE_MAPS_API_KEY).";
        return;
      }

      map = new google.maps.Map(document.getElementById("map"), {
        center: { lat: 33.5731, lng: -7.5898 },
        zoom: 11,
        mapTypeControl: false,
        streetViewControl: false,
      });
    }

    window.initGoogleMap = initGoogleMap;

    function setStatus(message, type = "") {
      statusEl.className = `status ${type}`.trim();
      statusEl.textContent = message;
    }

    function toFixedSafe(value) {
      if (typeof value !== "number") return "-";
      return value.toFixed(5);
    }

    function renderSummary(data) {
      intentEl.textContent = data.intent ?? "-";
      cityEl.textContent = data.city ?? "-";
      categoryEl.textContent = data.category ?? "-";
      nearMeEl.textContent = data.near_me ? "true" : "false";
    }

    function clearMapMarkers() {
      for (const marker of resultMarkers) {
        marker.setMap(null);
      }
      resultMarkers = [];
    }

    function getUserCoordsFromInputs() {
      const lat = Number(latInput.value);
      const lng = Number(lngInput.value);
      if (Number.isFinite(lat) && Number.isFinite(lng)) {
        return [lat, lng];
      }
      return null;
    }

    function renderMap(places) {
      if (!map) {
        return;
      }

      clearMapMarkers();

      const userCoords = getUserCoordsFromInputs();
      if (userMarker) {
        userMarker.setMap(null);
        userMarker = null;
      }

      if (userCoords) {
        userMarker = new google.maps.Marker({
          position: { lat: userCoords[0], lng: userCoords[1] },
          map,
          title: "Votre position",
          icon: {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 7,
            fillColor: "#0a9396",
            fillOpacity: 1,
            strokeColor: "#005f73",
            strokeWeight: 2,
          },
        })
      }

      const infoWindow = new google.maps.InfoWindow();

      if (!Array.isArray(places) || places.length === 0) {
        if (userCoords) {
          map.setCenter({ lat: userCoords[0], lng: userCoords[1] });
          map.setZoom(13);
          mapNoteEl.textContent = "Position utilisateur affichee, aucun lieu trouve.";
        } else {
          mapNoteEl.textContent = "Aucun lieu a afficher sur la carte.";
        }
        return;
      }

      const bounds = new google.maps.LatLngBounds();
      for (const place of places) {
        const lat = Number(place.latitude);
        const lng = Number(place.longitude);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
          continue;
        }

        const marker = new google.maps.Marker({
          position: { lat, lng },
          map,
        });
        const title = place.name ?? "Lieu";
        const addr = place.address ?? "Adresse indisponible";
        const desc = place.description ?? "Description indisponible";
        marker.addListener("click", () => {
          infoWindow.setContent(`<strong>${title}</strong><br>${desc}<br><small>${addr}</small>`);
          infoWindow.open({ anchor: marker, map });
        });

        resultMarkers.push(marker);
        bounds.extend({ lat, lng });
      }

      if (userCoords) {
        bounds.extend({ lat: userCoords[0], lng: userCoords[1] });
      }

      if (resultMarkers.length > 0 || userCoords) {
        map.fitBounds(bounds, 40);
      }

      mapNoteEl.textContent = `${resultMarkers.length} lieu(x) affiche(s) sur la carte.`;
    }

    function renderPlaces(places) {
      cardsEl.innerHTML = "";
      if (!Array.isArray(places) || places.length === 0) {
        cardsEl.innerHTML = `<div class="place"><h4>Aucun lieu</h4><p>La recherche n'a retourne aucun resultat.</p></div>`;
        return;
      }

      for (const place of places) {
        const card = document.createElement("article");
        card.className = "place";

        const rating = place.rating ?? "-";
        const mapsLink = place.google_maps_url
          ? `<a href="${place.google_maps_url}" target="_blank" rel="noreferrer">Ouvrir Maps</a>`
          : "";

        card.innerHTML = `
          <h4>${place.name ?? "Lieu"}</h4>
          <p>${place.description ?? "Description indisponible"}</p>
          <p>${place.address ?? "Adresse indisponible"}</p>
          <div class="meta">
            <span>Note: ${rating}</span>
            <span>${toFixedSafe(place.latitude)}, ${toFixedSafe(place.longitude)}</span>
          </div>
          <div class="links">${mapsLink}</div>
        `;

        cardsEl.appendChild(card);
      }
    }

    async function sendRequest() {
      const query = queryInput.value.trim();
      if (!query) {
        setStatus("La requete est obligatoire.", "error");
        return;
      }

      const payload = { query };
      const lat = latInput.value.trim();
      const lng = lngInput.value.trim();

      if (lat && lng) {
        payload.user_latitude = Number(lat);
        payload.user_longitude = Number(lng);
      }

      btnSend.disabled = true;
      setStatus("Appel en cours...", "");

      try {
        const response = await fetch("/api/ai/search", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        const rawText = await response.text();
        let data = {};
        try {
          data = rawText ? JSON.parse(rawText) : {};
        } catch {
          data = { error: { message: `Reponse non JSON: ${rawText.slice(0, 250)}` } };
        }

        if (!response.ok) {
          setStatus(data?.error?.message || "Erreur API", "error");
          jsonOutputEl.textContent = JSON.stringify(data, null, 2);
          cardsEl.innerHTML = "";
          renderMap([]);
          return;
        }

        renderSummary(data);
        renderPlaces(data.results);
        renderMap(data.results);
        jsonOutputEl.textContent = JSON.stringify(data, null, 2);
        setStatus(`Succes: ${data.results_count ?? 0} lieu(x) trouve(s).`, "ok");
      } catch (err) {
        setStatus(`Erreur reseau: ${err.message}`, "error");
      } finally {
        btnSend.disabled = false;
      }
    }

    function useMyLocation() {
      if (!navigator.geolocation) {
        setStatus("La geolocalisation n'est pas supportee par ce navigateur.", "error");
        return;
      }

      btnLocate.disabled = true;
      setStatus("Recuperation de votre position...", "");

      navigator.geolocation.getCurrentPosition(
        (position) => {
          const { latitude, longitude } = position.coords;
          latInput.value = latitude.toFixed(6);
          lngInput.value = longitude.toFixed(6);
          if (map) {
            map.setCenter({ lat: latitude, lng: longitude });
            map.setZoom(14);
          }

          if (userMarker) {
            userMarker.setMap(null);
          }

          if (map) {
            userMarker = new google.maps.Marker({
              position: { lat: latitude, lng: longitude },
              map,
              title: "Votre position",
              icon: {
                path: google.maps.SymbolPath.CIRCLE,
                scale: 7,
                fillColor: "#0a9396",
                fillOpacity: 1,
                strokeColor: "#005f73",
                strokeWeight: 2,
              },
            });
          }

          mapNoteEl.textContent = "Position detectee automatiquement.";
          setStatus("Position detectee. Vous pouvez lancer la recherche.", "ok");
          btnLocate.disabled = false;
        },
        (error) => {
          setStatus(`Impossible de recuperer la position: ${error.message}`, "error");
          btnLocate.disabled = false;
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 120000,
        }
      );
    }

    btnSend.addEventListener("click", sendRequest);
    btnLocate.addEventListener("click", useMyLocation);

    queryInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
        event.preventDefault();
        sendRequest();
      }
    });

    window.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && event.target === queryInput) {
        event.preventDefault();
        sendRequest();
      }
    });

    btnClear.addEventListener("click", () => {
      queryInput.value = "";
      latInput.value = "";
      lngInput.value = "";
      cardsEl.innerHTML = "";
      clearMapMarkers();
      if (userMarker) {
        userMarker.setMap(null);
        userMarker = null;
      }
      if (map) {
        map.setCenter({ lat: 33.5731, lng: -7.5898 });
        map.setZoom(11);
      }
      mapNoteEl.textContent = "Carte reinitialisee.";
      jsonOutputEl.textContent = "Aucune reponse pour le moment.";
      renderSummary({ intent: "-", city: "-", category: "-", near_me: false });
      setStatus("", "");
    });

    if (!googleMapsKey) {
      setStatus("GOOGLE_MAPS_API_KEY manquante: carte Google desactivee.", "error");
    } else {
      setStatus("Interface chargee. Autorisez la localisation, puis lancez le test.", "");
    }

    useMyLocation();
  </script>
</body>
</html>
"""
        .replace("__GOOGLE_MAPS_SCRIPT__", google_maps_script)
        .replace("__GOOGLE_MAPS_KEY__", google_maps_key)
    )
