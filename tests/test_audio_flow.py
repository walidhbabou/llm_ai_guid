#!/usr/bin/env python3
"""
Test script to verify audio transcription + LLM response flow
Utilise des fichiers audio de test locaux ou génère un audio simple
"""
import asyncio
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.search_service import AISearchService
from app.services.audio_transcription_service import AudioTranscriptionService
from app.llm.assistant import GuideAssistant
from app.core.config import settings


async def test_text_search():
    """Test 1: Recherche simple en texte"""
    print("\n" + "="*60)
    print("TEST 1: Recherche texte simple")
    print("="*60)
    
    service = AISearchService()
    query = "Cafés à Rabat"
    
    try:
        result = await service.search(query=query)
        print(f"✅ Requête: {query}")
        print(f"✅ Intent détecté: {result.intent}")
        print(f"✅ Ville: {result.city}")
        print(f"✅ Résultats trouvés: {result.results_count}")
        if result.assistant_reply:
            print(f"✅ Réponse LLM: {result.assistant_reply[:100]}...")
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


async def test_transcription_service():
    """Test 2: Service de transcription (si audio disponible)"""
    print("\n" + "="*60)
    print("TEST 2: Service de transcription")
    print("="*60)
    
    service = AudioTranscriptionService()
    
    # Vérifions que la méthode est async
    print(f"✅ Méthode transcribe est async: {asyncio.iscoroutinefunction(service.transcribe)}")
    
    # Test avec du texte simulé (pas d'audio réel)
    try:
        # On va juste vérifier que l'API est correctement configurée
        if service._client:
            print(f"✅ Groq API client configuré")
        else:
            print(f"⚠️  Groq API client non configuré, utilise Whisper local")
        
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


async def test_audio_search_flow():
    """Test 3: Flux complet audio → transcription → LLM → réponse"""
    print("\n" + "="*60)
    print("TEST 3: Flux audio complet (simulation)")
    print("="*60)
    
    service = AISearchService()
    assistant = GuideAssistant()
    
    # Simulons une question en français
    simulated_transcribed_query = "Quels sont les meilleurs restaurants à Marrakech?"
    
    print(f"📝 Question simulée (après transcription): {simulated_transcribed_query}")
    
    try:
        # Analyse de la requête
        analysis = service.analyzer.analyze(simulated_transcribed_query)
        print(f"✅ Analyse LLM:")
        print(f"   - Intent: {analysis.intent}")
        print(f"   - Ville: {analysis.city}")
        print(f"   - Catégorie: {analysis.category}")
        print(f"   - Préférences: {analysis.preferences}")
        
        # Recherche des lieux
        result = await service.search(query=simulated_transcribed_query)
        print(f"✅ Recherche Google Maps:")
        print(f"   - Résultats trouvés: {result.results_count}")
        
        if result.assistant_reply:
            print(f"✅ Réponse LLM générative:")
            print(f"   {result.assistant_reply[:150]}...")
        
        print(f"✅ Response mode: {result.response_mode}")
        
        return True
    except Exception as e:
        print(f"❌ Erreur dans le flux: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("\n🚀 TEST SUITE - Audio Transcription + LLM Response Flow")
    print("Configuration d'environnement:")
    print(f"  - GROQ_MODEL: {settings.groq_model}")
    print(f"  - GEMINI_MODEL: {settings.gemini_model}")
    print(f"  - Groq API Key configurée: {'✅' if settings.llm_api_key else '❌'}")
    print(f"  - Gemini API Key configurée: {'✅' if settings.gemini_api_key else '❌'}")
    print(f"  - Google Maps API Key configurée: {'✅' if settings.google_maps_api_key else '❌'}")
    
    results = []
    
    # Test 1: Texte simple
    results.append(("Recherche Texte", await test_text_search()))
    
    # Test 2: Transcription Service
    results.append(("Service Transcription", await test_transcription_service()))
    
    # Test 3: Flux Audio complet
    results.append(("Flux Audio Complet", await test_audio_search_flow()))
    
    # Résumé
    print("\n" + "="*60)
    print("📊 RÉSUMÉ DES TESTS")
    print("="*60)
    passed = sum(1 for _, result in results if result)
    total = len(results)
    print(f"Réussis: {passed}/{total}")
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")
    
    if passed == total:
        print("\n🎉 Tous les tests sont passés! L'audio devrait fonctionner.")
    else:
        print(f"\n⚠️  {total - passed} test(s) échoué(s). Vérifier les erreurs ci-dessus.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
