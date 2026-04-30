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
  <title>Assistant Touristique Texte + Audio</title>
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

    input, textarea, select {
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

    input:focus, textarea:focus, select:focus {
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

    .prompt-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: -2px 0 14px;
    }

    .prompt-chip {
      border: 1px solid #d6e4e8;
      background: linear-gradient(180deg, #f7fbfd 0%, #ffffff 100%);
      color: #21526b;
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 12px;
      cursor: pointer;
    }

    .audio-panel {
      margin-top: 14px;
      padding: 14px;
      border-radius: 14px;
      border: 1px solid #d6e4e8;
      background: linear-gradient(180deg, #f6fbfc 0%, #fff 100%);
    }

    .toggle {
      display: flex;
      align-items: center;
      gap: 8px;
      margin: 10px 0 0;
      color: var(--muted);
      font-size: 13px;
    }

    .toggle input {
      width: auto;
      margin: 0;
    }

    .voice-note {
      margin: 10px 0 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.45;
    }

    .audio-separator {
      margin: 14px 0 10px;
      border: 0;
      border-top: 1px dashed #c8d9de;
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

    .recording {
      background: var(--error);
      color: #fff;
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
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 10px;
      margin-bottom: 14px;
    }

    .assistant-card {
      background: linear-gradient(135deg, #fff7ec 0%, #fff 100%);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 14px;
      margin-bottom: 14px;
    }

    .assistant-card small {
      display: block;
      color: var(--muted);
      margin-bottom: 6px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.6px;
    }

    .assistant-card p {
      margin: 0;
      line-height: 1.5;
      color: #2f2a1f;
      font-size: 14px;
    }

    .suggestions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }

    .suggestion-chip {
      border: 1px solid #d8c9aa;
      background: #fffdf8;
      color: #6d5532;
      border-radius: 999px;
      padding: 8px 12px;
      font-size: 12px;
      cursor: pointer;
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

    .guide-card {
      background: linear-gradient(135deg, #eef8fb 0%, #fffdf8 100%);
      border-color: #cfe3ea;
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

    .photo-gallery {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(64px, 1fr));
      gap: 6px;
      margin: 8px 0 10px;
    }

    .photo-gallery a {
      display: block;
      border-radius: 10px;
      overflow: hidden;
      border: 1px solid #eadfca;
      background: #f7f3ea;
      aspect-ratio: 1 / 1;
    }

    .photo-gallery img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }

    .photo-gallery.more-only {
      grid-template-columns: repeat(auto-fit, minmax(88px, 1fr));
    }

    .photo-more {
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      padding: 8px;
      font-size: 11px;
      color: #6d5532;
      background: #fff8ef;
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

    .card-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 8px;
    }

    .guide-action {
      background: #ebf5f7;
      color: var(--accent);
      border: 1px solid #c8e1e8;
      font-size: 12px;
      padding: 8px 12px;
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
      <h1 class="title">Assistant Touristique</h1>
      <p class="subtitle">Posez une question naturelle comme "lieu romantique au coucher de soleil" ou "ville culturelle pour photos". L'assistant peut repondre en texte, par la voix, ou via un fichier audio.</p>

      <label for="query">Requete utilisateur</label>
      <textarea id="query" placeholder="Ex: un rooftop romantique a Rabat, une plage calme a Agadir, ou une ville culturelle pour photos"></textarea>

      <div class="prompt-list">
        <button class="prompt-chip" type="button" data-prompt="lieu romantique au coucher de soleil">lieu romantique au coucher de soleil</button>
        <button class="prompt-chip" type="button" data-prompt="ville culturelle pour photos">ville culturelle pour photos</button>
        <button class="prompt-chip" type="button" data-prompt="plage calme a Agadir">plage calme a Agadir</button>
        <button class="prompt-chip" type="button" data-prompt="sortie famille a Rabat">sortie famille a Rabat</button>
      </div>

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

      <section class="audio-panel">
        <label for="voice-lang">Langue du micro et de la lecture audio</label>
        <select id="voice-lang">
          <option value="fr-FR" selected>Francais</option>
          <option value="ar-MA">Arabe</option>
          <option value="en-US">Anglais</option>
        </select>

        <div class="actions">
          <button class="secondary" id="btn-voice-input" type="button">Parler</button>
          <button class="secondary" id="btn-play-reply" type="button" disabled>Lire la reponse</button>
          <button class="secondary" id="btn-stop-reply" type="button" disabled>Couper l'audio</button>
        </div>

        <hr class="audio-separator" />

        <label for="audio-file">Envoyer un vrai fichier audio au backend</label>
        <input id="audio-file" type="file" accept=".flac,.m4a,.mp3,.mp4,.mpeg,.mpga,.ogg,.wav,.webm,audio/*" />

        <div class="actions">
          <button class="secondary" id="btn-send-audio" type="button" disabled>Envoyer l'audio au backend</button>
          <button class="secondary" id="btn-record-audio" type="button">Enregistrer puis envoyer</button>
        </div>

        <p class="voice-note" id="audio-upload-note">Aucun fichier audio selectionne.</p>

        <label class="toggle" for="auto-speak">
          <input id="auto-speak" type="checkbox" checked />
          Lire automatiquement la reponse de l'assistant
        </label>

        <p class="voice-note" id="voice-support-note">Verification des capacites audio du navigateur...</p>
      </section>

      <div id="status" class="status"></div>
    </section>

    <section class="panel">
      <div class="head">
        <h2 style="margin:0;font-size:19px;">Resultats</h2>
        <span class="chip" id="api-badge">POST /api/ai/search</span>
      </div>

      <div class="summary" id="summary">
        <div class="metric"><small>Intent</small><strong id="intent">-</strong></div>
        <div class="metric"><small>Langue</small><strong id="language">-</strong></div>
        <div class="metric"><small>Ville</small><strong id="city">-</strong></div>
        <div class="metric"><small>Categorie</small><strong id="category">-</strong></div>
        <div class="metric"><small>Near Me</small><strong id="nearMe">-</strong></div>
      </div>

      <section class="assistant-card">
        <small>Reponse assistant</small>
        <p id="assistant-reply">Aucune reponse guide pour le moment.</p>
        <div class="suggestions" id="suggestions"></div>
      </section>

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
    const promptButtons = [...document.querySelectorAll("[data-prompt]")];
    const btnVoiceInput = document.getElementById("btn-voice-input");
    const btnSendAudio = document.getElementById("btn-send-audio");
    const btnRecordAudio = document.getElementById("btn-record-audio");
    const btnPlayReply = document.getElementById("btn-play-reply");
    const btnStopReply = document.getElementById("btn-stop-reply");
    const voiceLangSelect = document.getElementById("voice-lang");
    const audioFileInput = document.getElementById("audio-file");
    const autoSpeakCheckbox = document.getElementById("auto-speak");
    const audioUploadNoteEl = document.getElementById("audio-upload-note");
    const voiceSupportNoteEl = document.getElementById("voice-support-note");
    const statusEl = document.getElementById("status");
    const apiBadgeEl = document.getElementById("api-badge");

    const backendAudioEnabled = __AUDIO_BACKEND_ENABLED__;

    const intentEl = document.getElementById("intent");
    const languageEl = document.getElementById("language");
    const cityEl = document.getElementById("city");
    const categoryEl = document.getElementById("category");
    const nearMeEl = document.getElementById("nearMe");
    const assistantReplyEl = document.getElementById("assistant-reply");
    const suggestionsEl = document.getElementById("suggestions");
    const cardsEl = document.getElementById("cards");
    const jsonOutputEl = document.getElementById("json-output");
    const mapNoteEl = document.getElementById("map-note");

    const SpeechRecognitionApi = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognitionSupported = Boolean(SpeechRecognitionApi);
    const speechSupported =
      "speechSynthesis" in window && "SpeechSynthesisUtterance" in window;
    const mediaRecorderSupported = Boolean(
      window.MediaRecorder &&
      navigator.mediaDevices &&
      typeof navigator.mediaDevices.getUserMedia === "function"
    );

    let map = null;
    let resultMarkers = [];
    let userMarker = null;
    let routePolyline = null;
    let recognition = null;
    let isListening = false;
    let voiceSessionPrefix = "";
    let lastAssistantText = "";
    let mediaRecorder = null;
    let mediaRecorderStream = null;
    let recordedAudioChunks = [];
    let isRecordingUploadAudio = false;
    let isUploadingAudio = false;
    let discardRecordedAudioOnStop = false;

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

    function normalizeVoiceLang(lang) {
      const value = String(lang || "").toLowerCase();
      if (value.startsWith("fr")) return "fr-FR";
      if (value.startsWith("darija")) return "ar-MA";
      if (value.startsWith("ar")) return "ar-MA";
      if (value.startsWith("en")) return "en-US";
      return voiceLangSelect.value || "fr-FR";
    }

    function normalizeBackendAudioLanguage(lang) {
      const value = String(lang || "").toLowerCase();
      if (value.startsWith("fr")) return "fr";
      if (value.startsWith("ar")) return "ar";
      if (value.startsWith("en")) return "en";
      return "";
    }

    function pickVoice(lang) {
      if (!speechSupported) {
        return null;
      }

      const voices = window.speechSynthesis.getVoices();
      if (!voices.length) {
        return null;
      }

      const exactMatch = voices.find(
        (voice) => String(voice.lang || "").toLowerCase() === lang.toLowerCase()
      );
      if (exactMatch) {
        return exactMatch;
      }

      const prefix = lang.split("-")[0].toLowerCase();
      return (
        voices.find((voice) =>
          String(voice.lang || "").toLowerCase().startsWith(prefix)
        ) || null
      );
    }

    function updateVoiceInputButton() {
      btnVoiceInput.textContent = isListening ? "Arreter l'ecoute" : "Parler";
      btnVoiceInput.classList.toggle("recording", isListening);
      btnVoiceInput.classList.toggle("primary", isListening);
      btnVoiceInput.classList.toggle("secondary", !isListening);
      btnVoiceInput.disabled = !recognitionSupported;
    }

    function updateReplyAudioButtons() {
      btnPlayReply.disabled = !speechSupported || !lastAssistantText;
      btnStopReply.disabled = !speechSupported;
    }

    function updateAudioUploadButtons() {
      const hasSelectedFile = Boolean(audioFileInput.files && audioFileInput.files.length);
      btnSendAudio.disabled = isUploadingAudio || !hasSelectedFile || !backendAudioEnabled;
      btnRecordAudio.disabled =
        isUploadingAudio ||
        !backendAudioEnabled ||
        (!mediaRecorderSupported && !isRecordingUploadAudio);
      btnRecordAudio.textContent = isRecordingUploadAudio
        ? "Arreter puis envoyer"
        : "Enregistrer puis envoyer";
      btnRecordAudio.classList.toggle("recording", isRecordingUploadAudio);
      btnRecordAudio.classList.toggle("primary", isRecordingUploadAudio);
      btnRecordAudio.classList.toggle("secondary", !isRecordingUploadAudio);
    }

    function updateVoiceSupportNote() {
      const inputState = recognitionSupported
        ? "Saisie vocale disponible sur ce navigateur."
        : "Saisie vocale indisponible ici. Utilisez le texte ou testez Chrome/Edge.";
      const outputState = speechSupported
        ? "Lecture audio disponible."
        : "Lecture audio indisponible sur ce navigateur.";
      const uploadState = backendAudioEnabled
        ? mediaRecorderSupported
          ? "Envoi audio vers le backend disponible."
          : "Envoi micro vers le backend indisponible sur ce navigateur."
        : "Transcription backend indisponible (verifiez GROQ_API_KEY).";
      voiceSupportNoteEl.textContent = `${inputState} ${outputState} ${uploadState}`;
    }

    function stopSpeaking() {
      if (!speechSupported) {
        return;
      }

      window.speechSynthesis.cancel();
      updateReplyAudioButtons();
    }

    function speakText(text, detectedLanguage = null) {
      if (!speechSupported) {
        setStatus("La lecture audio n'est pas supportee par ce navigateur.", "error");
        return;
      }

      const cleanText = String(text || "").trim();
      if (!cleanText) {
        setStatus("Aucun texte disponible pour la lecture audio.", "error");
        return;
      }

      stopSpeaking();

      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.lang = normalizeVoiceLang(detectedLanguage);
      const selectedVoice = pickVoice(utterance.lang);
      if (selectedVoice) {
        utterance.voice = selectedVoice;
      }

      utterance.rate = 1;
      utterance.pitch = 1;
      utterance.onstart = () => {
        setStatus("Lecture audio en cours...", "");
        updateReplyAudioButtons();
      };
      utterance.onend = () => {
        setStatus("Lecture audio terminee.", "ok");
        updateReplyAudioButtons();
      };
      utterance.onerror = () => {
        setStatus("La lecture audio a ete interrompue.", "error");
        updateReplyAudioButtons();
      };

      window.speechSynthesis.speak(utterance);
      updateReplyAudioButtons();
    }

    function buildRecognition() {
      if (!recognitionSupported || recognition) {
        return recognition;
      }

      recognition = new SpeechRecognitionApi();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = voiceLangSelect.value || "fr-FR";

      recognition.onstart = () => {
        isListening = true;
        updateVoiceInputButton();
        setStatus("Micro actif. Parlez maintenant...", "");
      };

      recognition.onresult = (event) => {
        const finalChunks = [];
        let interimChunk = "";

        for (let index = 0; index < event.results.length; index += 1) {
          const transcript = event.results[index][0]?.transcript ?? "";
          if (event.results[index].isFinal) {
            finalChunks.push(transcript);
          } else {
            interimChunk += `${transcript} `;
          }
        }

        const mergedText = [voiceSessionPrefix, finalChunks.join(" "), interimChunk]
          .map((value) => String(value || "").trim())
          .filter(Boolean)
          .join(" ")
          .replace(/\\s+/g, " ")
          .trim();

        queryInput.value = mergedText;
      };

      recognition.onerror = (event) => {
        const errorCode = event?.error || "unknown";
        if (errorCode === "aborted") {
          return;
        }

        if (errorCode === "not-allowed") {
          setStatus("Micro refuse. Autorisez l'acces au microphone dans votre navigateur.", "error");
          return;
        }

        setStatus(`Erreur micro: ${errorCode}`, "error");
      };

      recognition.onend = () => {
        isListening = false;
        updateVoiceInputButton();
        if (queryInput.value.trim()) {
          setStatus("Transcription terminee. Vous pouvez envoyer la requete.", "ok");
        }
      };

      return recognition;
    }

    function toggleVoiceInput() {
      if (!recognitionSupported) {
        setStatus("La saisie vocale n'est pas supportee sur ce navigateur.", "error");
        return;
      }

      const recognizer = buildRecognition();
      if (!recognizer) {
        setStatus("Impossible d'initialiser la saisie vocale.", "error");
        return;
      }

      if (isListening) {
        recognizer.stop();
        return;
      }

      voiceSessionPrefix = queryInput.value.trim();
      recognizer.lang = voiceLangSelect.value || "fr-FR";

      try {
        recognizer.start();
      } catch {
        setStatus("Le micro est deja en cours d'utilisation. Patientez un instant.", "error");
      }
    }

    function toFixedSafe(value) {
      if (typeof value !== "number") return "-";
      return value.toFixed(5);
    }

    function renderSummary(data) {
      intentEl.textContent = data.intent ?? "-";
      languageEl.textContent = data.detected_language ?? "-";
      cityEl.textContent = data.city ?? "-";
      categoryEl.textContent = data.category ?? "-";
      nearMeEl.textContent = data.near_me ? "true" : "false";
    }

    function renderAssistantReply(data) {
      const replyText =
        data.assistant_reply ?? data.message ?? "Aucune reponse guide disponible.";
      assistantReplyEl.textContent = replyText;
      lastAssistantText =
        replyText === "Aucune reponse guide disponible." ? "" : replyText;
      updateReplyAudioButtons();
    }

    function renderSuggestedQuestions(data) {
      suggestionsEl.innerHTML = "";
      const suggestions = Array.isArray(data.suggested_questions) ? data.suggested_questions : [];
      for (const suggestion of suggestions) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "suggestion-chip";
        button.textContent = suggestion;
        button.addEventListener("click", () => {
          queryInput.value = suggestion;
          queryInput.focus();
        });
        suggestionsEl.appendChild(button);
      }
    }

    function clearMapMarkers() {
      for (const marker of resultMarkers) {
        marker.setMap(null);
      }
      resultMarkers = [];
      if (routePolyline) {
        routePolyline.setMap(null);
        routePolyline = null;
      }
    }

    function getUserCoordsFromInputs() {
      const lat = Number(latInput.value);
      const lng = Number(lngInput.value);
      if (Number.isFinite(lat) && Number.isFinite(lng)) {
        return [lat, lng];
      }
      return null;
    }

    function looksLikeTourProgram(data = {}) {
      const text = [
        data?.assistant_reply ?? "",
        ...(Array.isArray(data?.guide_cards) ? data.guide_cards.map((c) => String(c?.time_slot ?? "")) : []),
      ]
        .join(" ")
        .toLowerCase();
      return (
        text.includes("programme") ||
        text.includes("itineraire") ||
        text.includes("itinéraire") ||
        text.includes("day plan") ||
        text.includes("sortie")
      );
    }

    function distanceKm(a, b) {
      const toRad = (deg) => (deg * Math.PI) / 180;
      const lat1 = Number(a?.latitude);
      const lng1 = Number(a?.longitude);
      const lat2 = Number(b?.latitude);
      const lng2 = Number(b?.longitude);
      if (![lat1, lng1, lat2, lng2].every(Number.isFinite)) {
        return Number.POSITIVE_INFINITY;
      }
      const R = 6371;
      const dLat = toRad(lat2 - lat1);
      const dLng = toRad(lng2 - lng1);
      const q =
        Math.sin(dLat / 2) * Math.sin(dLat / 2) +
        Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) * Math.sin(dLng / 2);
      return 2 * R * Math.atan2(Math.sqrt(q), Math.sqrt(1 - q));
    }

    function buildRouteOrder(places, userCoords = null) {
      const valid = (Array.isArray(places) ? places : []).filter((p) =>
        Number.isFinite(Number(p?.latitude)) && Number.isFinite(Number(p?.longitude))
      );
      if (valid.length <= 2) {
        return valid;
      }

      const remaining = [...valid];
      const route = [];

      let current = null;
      if (Array.isArray(userCoords) && userCoords.length === 2) {
        const [ulat, ulng] = userCoords;
        current = { latitude: ulat, longitude: ulng };
      } else {
        current = remaining[0];
        route.push(current);
        remaining.splice(0, 1);
      }

      while (remaining.length > 0) {
        let bestIdx = 0;
        let bestDist = Number.POSITIVE_INFINITY;
        for (let i = 0; i < remaining.length; i += 1) {
          const d = distanceKm(current, remaining[i]);
          if (d < bestDist) {
            bestDist = d;
            bestIdx = i;
          }
        }
        const next = remaining.splice(bestIdx, 1)[0];
        route.push(next);
        current = next;
      }

      return route;
    }

    function renderMap(places, data = {}) {
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
        if ((data.response_mode ?? "") === "guide") {
          if (userCoords) {
            map.setCenter({ lat: userCoords[0], lng: userCoords[1] });
            map.setZoom(13);
            mapNoteEl.textContent = "Question de conseil: votre position est affichee, sans lieu precis a cartographier.";
          } else {
            mapNoteEl.textContent = "Question de conseil: aucun lieu precis a afficher sur la carte.";
          }
          return;
        }

        if (userCoords) {
          map.setCenter({ lat: userCoords[0], lng: userCoords[1] });
          map.setZoom(13);
          mapNoteEl.textContent = "Position utilisateur affichee, aucun lieu trouve.";
        } else {
          mapNoteEl.textContent = "Aucun lieu a afficher sur la carte.";
        }
        return;
      }

      const routePlaces = buildRouteOrder(places, userCoords);
      const shouldDrawRouteLine = routePlaces.length >= 2 && (looksLikeTourProgram(data) || routePlaces.length >= 3);
      const bounds = new google.maps.LatLngBounds();
      for (let idx = 0; idx < routePlaces.length; idx += 1) {
        const place = routePlaces[idx];
        const lat = Number(place.latitude);
        const lng = Number(place.longitude);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
          continue;
        }

        const marker = new google.maps.Marker({
          position: { lat, lng },
          map,
          label: shouldDrawRouteLine ? String(idx + 1) : undefined,
        });
        const title = place.name ?? "Lieu";
        const addr = place.address ?? "Adresse indisponible";
        const desc = place.description ?? "Description indisponible";
        const duration = Number(place.duration_minutes);
        const durationLabel = Number.isFinite(duration) && duration > 0 ? `~${duration} min` : "";
        marker.addListener("click", () => {
          infoWindow.setContent(`<strong>${title}</strong><br>${desc}<br><small>${addr}</small>` + (durationLabel ? `<br><small>Durée: ${durationLabel}</small>` : ""));
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

      if (shouldDrawRouteLine) {
        routePolyline = new google.maps.Polyline({
          path: routePlaces.map((p) => ({ lat: Number(p.latitude), lng: Number(p.longitude) })),
          geodesic: true,
          strokeColor: "#e76f51",
          strokeOpacity: 0.9,
          strokeWeight: 4,
        });
        routePolyline.setMap(map);
        mapNoteEl.textContent = `${resultMarkers.length} lieu(x) lies en programme (ordre 1 -> ${resultMarkers.length}).`;
      } else {
        mapNoteEl.textContent = `${resultMarkers.length} lieu(x) affiche(s) sur la carte.`;
      }
    }

    function renderGuideCards(cards) {
      cardsEl.innerHTML = "";
      if (!Array.isArray(cards) || cards.length === 0) {
        return false;
      }

      const normalizedCards = cards
        .map((item, index) => ({ item, index }))
        .sort((a, b) => {
          const aSlot = String(a.item?.time_slot ?? "");
          const bSlot = String(b.item?.time_slot ?? "");
          if (aSlot && bSlot && aSlot !== bSlot) {
            return aSlot.localeCompare(bSlot);
          }
          return a.index - b.index;
        })
        .map(({ item }) => item);

      for (const item of normalizedCards) {
        const card = document.createElement("article");
        card.className = "place guide-card";

        const slot = String(item.time_slot ?? "").trim();
        const duration = Number(item.duration_minutes);
        const durationLabel = Number.isFinite(duration) && duration > 0 ? `~${duration} min` : "";
        const bMin = Number(item.budget_min_mad);
        const bMax = Number(item.budget_max_mad);
        const budgetLabel =
          Number.isFinite(bMin) && Number.isFinite(bMax) && (bMin > 0 || bMax > 0)
            ? `${bMin}-${bMax} MAD / pers (approx)`
            : "";
        const metaLeft = [slot, durationLabel].filter(Boolean).join(" • ");
        const metaRight = budgetLabel;

        card.innerHTML = `
          <h4>${item.title ?? "Suggestion"}</h4>
          <p>${item.description ?? "Suggestion guide disponible."}</p>
          ${
            metaLeft || metaRight
              ? `<div class="meta"><span>${metaLeft || "-"}</span><span>${metaRight || ""}</span></div>`
              : ""
          }
          <div class="card-actions"></div>
        `;

        const actionsEl = card.querySelector(".card-actions");
        if (item.query && actionsEl) {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "guide-action";
          button.textContent = "Utiliser cette etape";
          button.addEventListener("click", () => {
            queryInput.value = item.query;
            queryInput.focus();
          });
          actionsEl.appendChild(button);
        }

        cardsEl.appendChild(card);
      }

      return true;
    }

    function renderGuideEmptyState(data) {
      const replyText =
        data.assistant_reply ??
        data.message ??
        "La demande a ete comprise, mais il n'y a pas de lieu precis a afficher pour cette question.";

      cardsEl.innerHTML = `
        <div class="place guide-card">
          <h4>Reponse conseil</h4>
          <p>${replyText}</p>
        </div>
      `;
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

        const mapsLink = place.google_maps_url
          ? `<a href="${place.google_maps_url}" target="_blank" rel="noreferrer">Ouvrir Maps</a>`
          : "";

        const duration = Number(place.duration_minutes);
        const durationLabel = Number.isFinite(duration) && duration > 0 ? `~${duration} min` : "";
        const photoUrls = Array.isArray(place.photo_urls) ? place.photo_urls.filter(Boolean) : [];
        const visiblePhotos = photoUrls.slice(0, 6);
        const extraPhotoCount = Math.max(0, photoUrls.length - visiblePhotos.length);
        const photoGallery = visiblePhotos.length
          ? `
            <div class="photo-gallery ${extraPhotoCount ? "more-only" : ""}">
              ${visiblePhotos
                .map(
                  (url, index) => `
                    <a href="${url}" target="_blank" rel="noreferrer" aria-label="Photo ${index + 1} de ${place.name ?? "ce lieu"}">
                      <img src="${url}" alt="Photo ${index + 1} de ${place.name ?? "ce lieu"}" loading="lazy" />
                    </a>
                  `
                )
                .join("")}
              ${
                extraPhotoCount
                  ? `<div class="photo-more">+${extraPhotoCount} autres photos</div>`
                  : ""
              }
            </div>
          `
          : "";

        card.innerHTML = `
          <h4>${place.name ?? "Lieu"}</h4>
          <p>${place.description ?? "Description indisponible"}</p>
          ${photoGallery}
          <p>${place.address ?? "Adresse indisponible"}</p>
          <div class="meta">
            <span>${toFixedSafe(place.latitude)}, ${toFixedSafe(place.longitude)}</span>
            ${durationLabel ? `<span>Durée: ${durationLabel}</span>` : ""}
          </div>
          <div class="links">${mapsLink}</div>
        `;

        cardsEl.appendChild(card);
      }
    }

    function renderResultCards(data) {
      const places = Array.isArray(data.results) ? data.results : [];
      if (places.length > 0) {
        renderPlaces(places);
        return;
      }

      const guideCards = Array.isArray(data.guide_cards) ? data.guide_cards : [];
      if (guideCards.length > 0) {
        renderGuideCards(guideCards);
        return;
      }

      if ((data.response_mode ?? "") === "guide") {
        renderGuideEmptyState(data);
        return;
      }

      renderPlaces([]);
    }

    async function parseApiResponse(response) {
      const rawText = await response.text();
      let data = {};
      try {
        data = rawText ? JSON.parse(rawText) : {};
      } catch {
        data = { error: { message: `Reponse non JSON: ${rawText.slice(0, 250)}` } };
      }
      return data;
    }

    function renderApiError(data) {
      setStatus(data?.error?.message || "Erreur API", "error");
      jsonOutputEl.textContent = JSON.stringify(data, null, 2);
      renderAssistantReply({});
      renderSuggestedQuestions({});
      cardsEl.innerHTML = "";
      renderMap([]);
    }

    function renderApiSuccess(data) {
      renderSummary(data);
      renderAssistantReply(data);
      renderSuggestedQuestions(data);
      renderResultCards(data);
      renderMap(data.results, data);
      jsonOutputEl.textContent = JSON.stringify(data, null, 2);

      if (data.transcribed_query) {
        queryInput.value = data.transcribed_query;
        audioUploadNoteEl.textContent = `Transcription: ${data.transcribed_query}`;
      }

      if (autoSpeakCheckbox.checked && lastAssistantText) {
        speakText(lastAssistantText, data.detected_language);
      }
    }

    function buildSuccessMessage(data, source = "text") {
      if ((data.response_mode ?? "") === "guide") {
        return source === "audio"
          ? "Audio transcrit puis reponse guide generee."
          : "Reponse guide generee.";
      }

      if (source === "audio") {
        if ((data.results_count ?? 0) > 0) {
          return `Audio transcrit puis traite: ${data.results_count ?? 0} lieu(x) trouve(s).`;
        }
        return "Audio transcrit puis reponse guide generee.";
      }

      if ((data.results_count ?? 0) > 0) {
        return `Succes: ${data.results_count ?? 0} lieu(x) trouve(s).`;
      }
      return "Reponse guide generee sans resultat cartographique.";
    }

    function getPreferredRecordingMimeType() {
      if (!mediaRecorderSupported) {
        return "";
      }

      if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
        return "audio/webm;codecs=opus";
      }
      if (MediaRecorder.isTypeSupported("audio/webm")) {
        return "audio/webm";
      }
      if (MediaRecorder.isTypeSupported("audio/ogg;codecs=opus")) {
        return "audio/ogg;codecs=opus";
      }
      return "";
    }

    async function sendAudioBlob(blob, filename) {
      if (!backendAudioEnabled) {
        setStatus("Transcription backend indisponible (verifiez GROQ_API_KEY).", "error");
        return;
      }

      if (!blob || blob.size === 0) {
        setStatus("Le fichier audio est vide ou invalide.", "error");
        return;
      }

      if (isListening && recognition) {
        recognition.stop();
      }
      stopSpeaking();

      isUploadingAudio = true;
      btnSend.disabled = true;
      apiBadgeEl.textContent = "POST /api/ai/search/audio";
      updateAudioUploadButtons();
      setStatus("Envoi de l'audio au backend...", "");

      try {
        const payload = new FormData();
        payload.append("audio", blob, filename);

        const lat = latInput.value.trim();
        const lng = lngInput.value.trim();
        const language = normalizeBackendAudioLanguage(voiceLangSelect.value);

        if (lat && lng) {
          payload.append("user_latitude", lat);
          payload.append("user_longitude", lng);
        }
        if (language) {
          payload.append("language", language);
        }

        const response = await fetch("/api/ai/search/audio", {
          method: "POST",
          body: payload,
        });

        const data = await parseApiResponse(response);
        if (!response.ok) {
          renderApiError(data);
          return;
        }

        renderApiSuccess(data);
        setStatus(buildSuccessMessage(data, "audio"), "ok");
      } catch (err) {
        setStatus(`Erreur reseau: ${err.message}`, "error");
      } finally {
        isUploadingAudio = false;
        btnSend.disabled = false;
        updateAudioUploadButtons();
      }
    }

    async function sendSelectedAudioFile() {
      if (!backendAudioEnabled) {
        setStatus("Transcription backend indisponible (verifiez GROQ_API_KEY).", "error");
        return;
      }

      const file = audioFileInput.files && audioFileInput.files[0];
      if (!file) {
        setStatus("Choisissez un fichier audio avant l'envoi.", "error");
        return;
      }

      audioUploadNoteEl.textContent = `Fichier pret: ${file.name}`;
      await sendAudioBlob(file, file.name || `question-${Date.now()}.webm`);
    }

    async function toggleAudioRecording() {
      if (!backendAudioEnabled) {
        setStatus("Transcription backend indisponible (verifiez GROQ_API_KEY).", "error");
        return;
      }

      if (isRecordingUploadAudio && mediaRecorder) {
        mediaRecorder.stop();
        return;
      }

      if (!mediaRecorderSupported) {
        setStatus("L'enregistrement audio n'est pas supporte ici.", "error");
        return;
      }

      if (isListening && recognition) {
        recognition.stop();
      }

      try {
        mediaRecorderStream = await navigator.mediaDevices.getUserMedia({ audio: true });
        recordedAudioChunks = [];
        const mimeType = getPreferredRecordingMimeType();
        mediaRecorder = mimeType
          ? new MediaRecorder(mediaRecorderStream, { mimeType })
          : new MediaRecorder(mediaRecorderStream);

        mediaRecorder.ondataavailable = (event) => {
          if (event.data && event.data.size > 0) {
            recordedAudioChunks.push(event.data);
          }
        };

        mediaRecorder.onerror = () => {
          setStatus("Erreur pendant l'enregistrement audio.", "error");
        };

        mediaRecorder.onstop = async () => {
          isRecordingUploadAudio = false;
          updateAudioUploadButtons();

          if (mediaRecorderStream) {
            for (const track of mediaRecorderStream.getTracks()) {
              track.stop();
            }
            mediaRecorderStream = null;
          }

          if (discardRecordedAudioOnStop) {
            discardRecordedAudioOnStop = false;
            recordedAudioChunks = [];
            audioUploadNoteEl.textContent = "Enregistrement annule.";
            return;
          }

          const recordedType = mediaRecorder?.mimeType || mimeType || "audio/webm";
          const blob = new Blob(recordedAudioChunks, { type: recordedType });
          recordedAudioChunks = [];

          if (!blob.size) {
            setStatus("Aucun son detecte pendant l'enregistrement.", "error");
            return;
          }

          audioUploadNoteEl.textContent = "Enregistrement termine. Envoi en cours...";
          const extension = recordedType.includes("ogg") ? "ogg" : "webm";
          await sendAudioBlob(blob, `question-${Date.now()}.${extension}`);
        };

        mediaRecorder.start();
        isRecordingUploadAudio = true;
        updateAudioUploadButtons();
        audioUploadNoteEl.textContent = "Enregistrement en cours...";
        setStatus("Enregistrement audio en cours. Cliquez encore pour arreter et envoyer.", "");
      } catch (err) {
        setStatus(`Impossible d'acceder au micro: ${err.message}`, "error");
        if (mediaRecorderStream) {
          for (const track of mediaRecorderStream.getTracks()) {
            track.stop();
          }
          mediaRecorderStream = null;
        }
      }
    }

    async function sendRequest() {
      const query = queryInput.value.trim();
      if (!query) {
        setStatus("La requete est obligatoire.", "error");
        return;
      }

      if (isListening && recognition) {
        recognition.stop();
      }
      stopSpeaking();

      const payload = { query };
      const lat = latInput.value.trim();
      const lng = lngInput.value.trim();

      if (lat && lng) {
        payload.user_latitude = Number(lat);
        payload.user_longitude = Number(lng);
      }

      btnSend.disabled = true;
      apiBadgeEl.textContent = "POST /api/ai/search";
      setStatus("Appel en cours...", "");

      try {
        const response = await fetch("/api/ai/search", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        });

        const data = await parseApiResponse(response);

        if (!response.ok) {
          renderApiError(data);
          return;
        }

        renderApiSuccess(data);
        setStatus(buildSuccessMessage(data, "text"), "ok");
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
    btnVoiceInput.addEventListener("click", toggleVoiceInput);
    btnSendAudio.addEventListener("click", sendSelectedAudioFile);
    btnRecordAudio.addEventListener("click", toggleAudioRecording);
    btnPlayReply.addEventListener("click", () => {
      speakText(lastAssistantText, languageEl.textContent);
    });
    btnStopReply.addEventListener("click", stopSpeaking);

    audioFileInput.addEventListener("change", () => {
      const file = audioFileInput.files && audioFileInput.files[0];
      audioUploadNoteEl.textContent = file
        ? `Fichier selectionne: ${file.name}`
        : "Aucun fichier audio selectionne.";
      updateAudioUploadButtons();
    });

    voiceLangSelect.addEventListener("change", () => {
      if (recognition) {
        recognition.lang = voiceLangSelect.value || "fr-FR";
      }
    });

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

    for (const button of promptButtons) {
      button.addEventListener("click", () => {
        queryInput.value = button.dataset.prompt ?? "";
        queryInput.focus();
      });
    }

    btnClear.addEventListener("click", () => {
      if (isListening && recognition) {
        recognition.stop();
      }
      if (isRecordingUploadAudio && mediaRecorder) {
        discardRecordedAudioOnStop = true;
        mediaRecorder.stop();
      }
      stopSpeaking();
      queryInput.value = "";
      latInput.value = "";
      lngInput.value = "";
      audioFileInput.value = "";
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
      assistantReplyEl.textContent = "Aucune reponse guide pour le moment.";
      lastAssistantText = "";
      updateReplyAudioButtons();
      audioUploadNoteEl.textContent = "Aucun fichier audio selectionne.";
      apiBadgeEl.textContent = "POST /api/ai/search";
      updateAudioUploadButtons();
      suggestionsEl.innerHTML = "";
      renderSummary({ intent: "-", detected_language: "-", city: "-", category: "-", near_me: false });
      setStatus("", "");
    });

    updateVoiceSupportNote();
    updateVoiceInputButton();
    updateReplyAudioButtons();
    updateAudioUploadButtons();

    if (!backendAudioEnabled) {
      audioUploadNoteEl.textContent = "Transcription backend indisponible (verifiez GROQ_API_KEY).";
    }

    if (speechSupported && "onvoiceschanged" in window.speechSynthesis) {
      window.speechSynthesis.onvoiceschanged = updateVoiceSupportNote;
    }

    if (!googleMapsKey) {
      setStatus("GOOGLE_MAPS_API_KEY manquante: carte Google desactivee.", "error");
    } else {
      setStatus("Interface chargee. Vous pouvez ecrire, parler, puis ecouter la reponse.", "");
    }

    useMyLocation();
  </script>
</body>
</html>
"""
        .replace("__GOOGLE_MAPS_SCRIPT__", google_maps_script)
        .replace("__GOOGLE_MAPS_KEY__", google_maps_key)
        .replace("__AUDIO_BACKEND_ENABLED__", "true" if settings.llm_enabled else "false")
    )
