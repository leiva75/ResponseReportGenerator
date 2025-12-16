"""
Security Meeting Questionnaire Module

Handles saving, loading, and managing security meeting questionnaires for venues.
Uses JSON file storage linked by venue identifier.
"""

import os
import json
import uuid
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from services.paths import get_questionnaire_file, get_data_dir

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

QUESTIONNAIRE_FILE = str(get_questionnaire_file())


def ensure_data_directory() -> bool:
    data_dir = get_data_dir()
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as e:
        logger.error(f"Failed to create data directory: {e}")
        return False


def generate_venue_id(venue_name: str, venue_address: str) -> str:
    combined = f"{venue_name.lower().strip()}|{venue_address.lower().strip()}"
    return hashlib.md5(combined.encode()).hexdigest()[:12]


def load_questionnaires() -> Dict[str, Dict]:
    if not ensure_data_directory():
        return {}
    
    if not os.path.exists(QUESTIONNAIRE_FILE):
        return {}
    
    try:
        with open(QUESTIONNAIRE_FILE, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {}
            data = json.loads(content)
            return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Failed to load questionnaires: {e}")
        return {}


def save_questionnaires(data: Dict) -> bool:
    if not ensure_data_directory():
        return False
    
    try:
        with open(QUESTIONNAIRE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        logger.error(f"Failed to save questionnaires: {e}")
        return False


def get_empty_questionnaire() -> Dict:
    return {
        'external_threat_description': '',
        'external_threat_meeting_point': '',
        'fire_gathering_points': '',
        'screening_walk_through': False,
        'screening_handheld': False,
        'screening_pat_down': False,
        'screening_bag_checks': False,
        'missing_child_protocol': '',
        'missing_child_notes': '',
        'backstage_id_required': False,
        'backstage_escort_required': False,
        'backstage_sign_in_required': False,
        'backstage_notes': '',
        'security_company_name': '',
        'security_supervisors': 0,
        'security_guards': 0,
        'security_traffic_management': 0,
        'security_ticket_checkers': 0,
        'security_ushers': 0,
        'security_medics': 0,
        'security_other': 0,
        'security_other_description': '',
        'general_cctv_operational': '',
        'general_lighting_adequate': '',
        'general_emergency_exits_clear': '',
        'general_fire_extinguishers': '',
        'general_first_aid_kits': '',
        'general_communication_radios': '',
        'crowd_capacity_limits': '',
        'crowd_barrier_placement': '',
        'crowd_queuing_system': '',
        'crowd_vip_separate_access': '',
        'crowd_disabled_access': '',
        'medical_ambulance_onsite': '',
        'medical_paramedics_count': 0,
        'medical_first_aiders_count': 0,
        'medical_hospital_distance': '',
        'medical_policy_notes': '',
        'additional_notes': ''
    }


def get_questionnaire(venue_name: str, venue_address: str) -> Optional[Dict]:
    venue_id = generate_venue_id(venue_name, venue_address)
    questionnaires = load_questionnaires()
    return questionnaires.get(venue_id)


def get_questionnaire_by_id(questionnaire_id: str) -> Optional[Dict]:
    questionnaires = load_questionnaires()
    return questionnaires.get(questionnaire_id)


def save_questionnaire(venue_name: str, venue_address: str, city: str, country: str, data: Dict, linked_report_id: Optional[str] = None) -> Optional[str]:
    venue_id = generate_venue_id(venue_name, venue_address)
    questionnaires = load_questionnaires()
    
    now = datetime.now()
    
    if venue_id in questionnaires:
        questionnaires[venue_id]['updated_at'] = now.isoformat()
        questionnaires[venue_id]['updated_at_formatted'] = now.strftime('%Y-%m-%d %H:%M')
        questionnaires[venue_id]['data'] = data
        if linked_report_id:
            questionnaires[venue_id]['linked_report_id'] = linked_report_id
    else:
        entry = {
            'id': venue_id,
            'venue_name': venue_name,
            'venue_address': venue_address,
            'city': city,
            'country': country,
            'created_at': now.isoformat(),
            'created_at_formatted': now.strftime('%Y-%m-%d %H:%M'),
            'updated_at': now.isoformat(),
            'updated_at_formatted': now.strftime('%Y-%m-%d %H:%M'),
            'data': data
        }
        if linked_report_id:
            entry['linked_report_id'] = linked_report_id
        questionnaires[venue_id] = entry
    
    if save_questionnaires(questionnaires):
        logger.info(f"Questionnaire saved for venue {venue_id}")
        return venue_id
    return None


def link_questionnaire_to_report(questionnaire_id: str, report_id: str) -> bool:
    """Link a questionnaire to a history report by ID."""
    questionnaires = load_questionnaires()
    
    if questionnaire_id in questionnaires:
        questionnaires[questionnaire_id]['linked_report_id'] = report_id
        questionnaires[questionnaire_id]['updated_at'] = datetime.now().isoformat()
        if save_questionnaires(questionnaires):
            logger.info(f"Linked questionnaire {questionnaire_id} to report {report_id}")
            return True
    return False


def get_questionnaire_by_report_id(report_id: str) -> Optional[Dict]:
    """Get questionnaire linked to a specific report."""
    questionnaires = load_questionnaires()
    for q_id, q in questionnaires.items():
        if q.get('linked_report_id') == report_id:
            return q
    return None


def delete_questionnaire(venue_name: str, venue_address: str) -> bool:
    venue_id = generate_venue_id(venue_name, venue_address)
    questionnaires = load_questionnaires()
    
    if venue_id in questionnaires:
        del questionnaires[venue_id]
        return save_questionnaires(questionnaires)
    return False


def list_all_questionnaires() -> List[Dict]:
    questionnaires = load_questionnaires()
    result = []
    
    for venue_id, q in questionnaires.items():
        result.append({
            'id': venue_id,
            'venue_name': q.get('venue_name', ''),
            'venue_address': q.get('venue_address', ''),
            'city': q.get('city', ''),
            'country': q.get('country', ''),
            'created_at_formatted': q.get('created_at_formatted', ''),
            'updated_at_formatted': q.get('updated_at_formatted', '')
        })
    
    result.sort(key=lambda x: x.get('updated_at_formatted', ''), reverse=True)
    return result
