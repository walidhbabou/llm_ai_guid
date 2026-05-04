import asyncio
import json
from app.services.search_service import AISearchService

async def test():
    service = AISearchService()
    result = await service.search(
        query='Cafes a Montpellier',
        user_latitude=43.6108,
        user_longitude=3.8767
    )
    print('=== RESULTATS ===')
    print(f'Nombre de lieux: {result.results_count}')
    print(f'\n=== DESCRIPTIONS DES PLACES (doivent être None/vides) ===')
    for place in result.results[:3]:
        print(f'  • {place.name}')
        print(f'    Description: {place.description}')
    print(f'\n=== REPONSE ASSISTANT (Gemini genere maintenant les descriptions) ===')
    print(f'{result.assistant_reply}')

if __name__ == '__main__':
    asyncio.run(test())
