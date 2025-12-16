"""
Translation service for converting French form data to English for reports.
Uses OpenAI API for accurate translations.
"""

import os
import json
import re

try:
    from openai import OpenAI
    openai_available = True
except ImportError:
    openai_available = False

openai_client = None

def init_openai():
    global openai_client
    if not openai_available:
        return False
    
    api_key = os.environ.get('AI_INTEGRATIONS_OPENAI_API_KEY') or os.environ.get('OPENAI_API_KEY')
    base_url = os.environ.get('AI_INTEGRATIONS_OPENAI_BASE_URL') or os.environ.get('OPENAI_BASE_URL')
    
    if not api_key:
        return False
    
    try:
        if base_url:
            openai_client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            openai_client = OpenAI(api_key=api_key)
        return True
    except Exception:
        return False


def translate_text(text: str) -> str:
    """Translate a single text from French to English."""
    if not text or not text.strip():
        return text
    
    global openai_client
    if openai_client is None:
        if not init_openai():
            return text
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a professional translator. Translate the following text from French to English.
Rules:
- Keep proper nouns (hotel names, city names, addresses) unchanged
- Maintain the original formatting and punctuation
- If the text is already in English, return it unchanged
- If the text contains mixed French/English, translate only the French parts
- Keep numbers, measurements, and technical terms accurate
- Return ONLY the translated text, no explanations"""
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        translated = response.choices[0].message.content
        return translated.strip() if translated else text
        
    except Exception as e:
        print(f"Translation error: {e}")
        return text


def translate_form_data(form_data: dict) -> dict:
    """Translate all French text fields in form_data to English."""
    if not form_data:
        return form_data
    
    translated_data = form_data.copy()
    
    fields_to_translate = [
        'hotel1_rooms_floors', 'hotel1_distance_venue', 'hotel1_facilities',
        'hotel1_wifi', 'hotel1_surrounding', 'hotel1_safety', 'hotel1_security_staff',
        'hotel1_entrances', 'hotel1_carpark', 'hotel1_cctv_access', 'hotel1_condition',
        'hotel1_overlapping',
        'hotel2_rooms_floors', 'hotel2_distance_venue', 'hotel2_facilities',
        'hotel2_wifi', 'hotel2_surrounding', 'hotel2_safety', 'hotel2_security_staff',
        'hotel2_entrances', 'hotel2_carpark', 'hotel2_cctv_access', 'hotel2_condition',
        'hotel2_overlapping',
        'transport_airport', 'transport_description',
        'venue_description', 'venue_photos_video', 'venue_parking',
        'venue_entrance_access', 'venue_branding', 'venue_tv_advertising',
        'venue_bowl_seating', 'venue_covid_provisions', 'venue_backstage',
        'venue_response_k9', 'venue_fcp_bootleggers', 'venue_recommendations',
        'venue_security_provisions'
    ]
    
    texts_to_translate = {}
    for field in fields_to_translate:
        value = form_data.get(field, '')
        if value and isinstance(value, str) and value.strip():
            texts_to_translate[field] = value
    
    if not texts_to_translate:
        return translated_data
    
    global openai_client
    if openai_client is None:
        if not init_openai():
            return translated_data
    
    try:
        batch_text = json.dumps(texts_to_translate, ensure_ascii=False, indent=2)
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a professional translator for security reports. Translate the JSON values from French to English.

Rules:
- Keep all JSON keys unchanged
- Translate only the values
- Keep proper nouns (hotel names, venue names, addresses, city names) unchanged
- Maintain formatting and punctuation
- If a value is already in English, keep it unchanged
- Keep numbers, measurements, and technical terms accurate
- Return ONLY valid JSON with the same structure

Common translations:
- "WiFi gratuit" → "Free WiFi"
- "Salle de fitness" → "Gym/Fitness center"
- "Piscine" → "Pool"
- "Restaurant" → "Restaurant"
- "Réception 24h/24" → "24h reception"
- "Sécurité 24h/24" → "24h security"
- "Vidéosurveillance" → "CCTV surveillance"
- "Accès par carte-clé" → "Key card access"
- "parking bus disponible" → "coach parking available"
- "chambres" → "rooms"
- "étages" → "floors"
- "min en voiture" → "min by car"
- "min à pied" → "min walk"
- "payant" → "paid"
- "gratuit" → "free"
- "places" → "spaces"
- "Petit-déjeuner seulement" → "Breakfast only"
- "Réceptionniste de nuit" → "Night receptionist" """
                },
                {
                    "role": "user",
                    "content": batch_text
                }
            ],
            temperature=0.2,
            max_tokens=4000
        )
        
        result_text = response.choices[0].message.content
        if result_text:
            result_text = result_text.strip()
            if result_text.startswith('```'):
                result_text = re.sub(r'^```(?:json)?\s*', '', result_text)
                result_text = re.sub(r'\s*```$', '', result_text)
            
            translated_fields = json.loads(result_text)
            
            for field, translated_value in translated_fields.items():
                if field in fields_to_translate:
                    translated_data[field] = translated_value
        
    except Exception as e:
        print(f"Batch translation error: {e}")
    
    return translated_data


def translate_security_data(security_data: dict) -> dict:
    """Translate security data comments from French to English."""
    if not security_data:
        return security_data
    
    translated_security = {}
    
    comments_to_translate = {}
    for key, item in security_data.items():
        translated_security[key] = item.copy()
        comment = item.get('comment', '')
        if comment and isinstance(comment, str) and comment.strip():
            comments_to_translate[key] = comment
    
    if not comments_to_translate:
        return translated_security
    
    global openai_client
    if openai_client is None:
        if not init_openai():
            return translated_security
    
    try:
        batch_text = json.dumps(comments_to_translate, ensure_ascii=False, indent=2)
        
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """You are a professional translator for security reports. Translate the JSON values from French to English.
Keep all JSON keys unchanged. Translate only the values.
Return ONLY valid JSON with the same structure."""
                },
                {
                    "role": "user",
                    "content": batch_text
                }
            ],
            temperature=0.2,
            max_tokens=2000
        )
        
        result_text = response.choices[0].message.content
        if result_text:
            result_text = result_text.strip()
            if result_text.startswith('```'):
                result_text = re.sub(r'^```(?:json)?\s*', '', result_text)
                result_text = re.sub(r'\s*```$', '', result_text)
            
            translated_comments = json.loads(result_text)
            
            for key, translated_comment in translated_comments.items():
                if key in translated_security:
                    translated_security[key]['comment'] = translated_comment
        
    except Exception as e:
        print(f"Security translation error: {e}")
    
    return translated_security
