"""
History Persistence Module

Handles saving and loading report history using a JSON file.
Each report is saved with a timestamp, event details, and all form data.
Uses atomic writes and backup mechanisms to prevent data loss.
"""

import json
import uuid
import shutil
import logging
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any

from services.paths import get_history_file, get_history_backup_file, get_data_dir

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

HISTORY_FILE: Path = get_history_file()
BACKUP_FILE: Path = get_history_backup_file()
MAX_HISTORY_SIZE = 100


def ensure_data_directory() -> bool:
    """
    Ensure the data directory exists.
    
    Returns:
        True if directory exists or was created, False on failure.
    """
    data_dir = get_data_dir()
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        return True
    except OSError as e:
        logger.error(f"Failed to create data directory: {e}")
        return False


def validate_report(report: Any) -> bool:
    """
    Validate that a report has the required structure.
    
    Args:
        report: The report data to validate.
        
    Returns:
        True if valid, False otherwise.
    """
    if not isinstance(report, dict):
        return False
    required_fields = ['id', 'created_at']
    return all(field in report for field in required_fields)


def load_history(attempt_restore: bool = True) -> List[Dict]:
    """
    Load all reports from the history file.
    
    Args:
        attempt_restore: Whether to attempt restoration from backup if primary is corrupt.
                        Used internally to prevent infinite recursion.
    
    Returns:
        List of report dictionaries, sorted by date (newest first).
        Returns empty list if file doesn't exist or on error.
    """
    if not ensure_data_directory():
        return []
    
    if not HISTORY_FILE.exists():
        return []
    
    try:
        content = HISTORY_FILE.read_text(encoding='utf-8').strip()
        if not content:
            return []
        history = json.loads(content)
        
        if not isinstance(history, list):
            logger.warning("History file contains invalid data structure, returning empty list")
            return []
        
        valid_history = [r for r in history if validate_report(r)]
        if len(valid_history) != len(history):
            logger.warning(f"Filtered out {len(history) - len(valid_history)} invalid report entries")
        
        valid_history.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return valid_history
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse history JSON: {e}")
        if attempt_restore and BACKUP_FILE.exists():
            logger.info("Attempting to restore from backup...")
            try:
                shutil.copy2(BACKUP_FILE, HISTORY_FILE)
                return load_history(attempt_restore=False)
            except Exception as restore_error:
                logger.error(f"Failed to restore from backup: {restore_error}")
        return []
    except IOError as e:
        logger.error(f"Failed to read history file: {e}")
        return []


def save_history(history: List[Dict]) -> bool:
    """
    Save the history list to the JSON file using atomic write.
    
    Uses a temporary file and rename to prevent corruption during write.
    Creates a backup of the existing file before overwriting.
    
    Args:
        history: List of report dictionaries.
        
    Returns:
        True if successful, False otherwise.
    """
    if not ensure_data_directory():
        return False
    
    if not isinstance(history, list):
        logger.error("Cannot save history: data is not a list")
        return False
    
    try:
        if HISTORY_FILE.exists():
            try:
                shutil.copy2(HISTORY_FILE, BACKUP_FILE)
            except Exception as backup_error:
                logger.warning(f"Failed to create backup: {backup_error}")
        
        data_dir = HISTORY_FILE.parent
        fd, temp_path = tempfile.mkstemp(suffix='.json', dir=str(data_dir))
        temp_file = Path(temp_path)
        
        try:
            with open(fd, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
            
            shutil.move(str(temp_file), str(HISTORY_FILE))
            return True
            
        except Exception as write_error:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
            raise write_error
            
    except Exception as e:
        logger.error(f"Failed to save history: {e}")
        return False


def add_report_to_history(form_data: Dict, security_data: Dict, pdf_filename: Optional[str] = None, is_draft: bool = False) -> Optional[str]:
    """
    Add a new report to the history.
    
    Args:
        form_data: The form data dictionary.
        security_data: The security items data.
        pdf_filename: Optional filename of the generated PDF.
        is_draft: Whether this is a draft (incomplete) report.
        
    Returns:
        The report ID if successful, None otherwise.
    """
    if not isinstance(form_data, dict):
        logger.error("Cannot add report: form_data is not a dictionary")
        return None
    
    history = load_history()
    
    report_id = str(uuid.uuid4())[:8]
    now = datetime.now()
    
    from services.security_questionnaire import get_questionnaire, link_questionnaire_to_report
    
    venue_name = form_data.get('venue_name', '')
    venue_address = form_data.get('venue_address', '')
    questionnaire_id = None
    
    if venue_name and venue_address:
        existing_q = get_questionnaire(venue_name, venue_address)
        if existing_q:
            questionnaire_id = existing_q.get('id')
    
    report = {
        'id': report_id,
        'created_at': now.isoformat(),
        'created_at_formatted': now.strftime('%Y-%m-%d %H:%M'),
        'event_type': form_data.get('event_type', 'Disney On Ice'),
        'city': form_data.get('event_city', ''),
        'venue_name': venue_name,
        'venue_address': venue_address,
        'hotel_name': form_data.get('hotel1_name', ''),
        'hotel2_name': form_data.get('hotel2_name', '') if form_data.get('has_two_hotels') else '',
        'event_start_date': form_data.get('event_start_date', ''),
        'event_end_date': form_data.get('event_end_date', ''),
        'pdf_filename': pdf_filename,
        'form_data': form_data.copy(),
        'security_data': security_data.copy() if security_data else {},
        'questionnaire_id': questionnaire_id,
        'is_draft': is_draft,
        'status': 'draft' if is_draft else 'completed'
    }
    
    history.insert(0, report)
    
    if len(history) > MAX_HISTORY_SIZE:
        history = history[:MAX_HISTORY_SIZE]
    
    if save_history(history):
        logger.info(f"Report {report_id} ({'draft' if is_draft else 'completed'}) added to history")
        if questionnaire_id:
            try:
                link_questionnaire_to_report(questionnaire_id, report_id)
            except Exception as e:
                logger.warning(f"Failed to link questionnaire {questionnaire_id} to report {report_id}: {e}")
        return report_id
    
    logger.error(f"Failed to save report {report_id} to history")
    return None


def update_draft(report_id: str, form_data: Dict, security_data: Dict) -> bool:
    """
    Update an existing draft report.
    
    Args:
        report_id: The unique report ID.
        form_data: The updated form data dictionary.
        security_data: The updated security items data.
        
    Returns:
        True if updated successfully, False otherwise.
    """
    if not report_id or not isinstance(report_id, str):
        logger.warning("Cannot update draft: invalid report_id")
        return False
    
    history = load_history()
    now = datetime.now()
    
    for i, report in enumerate(history):
        if report.get('id') == report_id:
            history[i]['updated_at'] = now.isoformat()
            history[i]['updated_at_formatted'] = now.strftime('%Y-%m-%d %H:%M')
            history[i]['event_type'] = form_data.get('event_type', 'Disney On Ice')
            history[i]['city'] = form_data.get('event_city', '')
            history[i]['venue_name'] = form_data.get('venue_name', '')
            history[i]['hotel_name'] = form_data.get('hotel1_name', '')
            history[i]['hotel2_name'] = form_data.get('hotel2_name', '') if form_data.get('has_two_hotels') else ''
            history[i]['event_start_date'] = form_data.get('event_start_date', '')
            history[i]['event_end_date'] = form_data.get('event_end_date', '')
            history[i]['form_data'] = form_data.copy()
            history[i]['security_data'] = security_data.copy() if security_data else {}
            
            if save_history(history):
                logger.info(f"Draft {report_id} updated")
                return True
            return False
    
    logger.warning(f"Draft {report_id} not found")
    return False


def convert_draft_to_completed(report_id: str, pdf_filename: Optional[str] = None) -> bool:
    """
    Convert a draft to a completed report.
    
    Args:
        report_id: The unique report ID.
        pdf_filename: Optional filename of the generated PDF.
        
    Returns:
        True if converted successfully, False otherwise.
    """
    if not report_id or not isinstance(report_id, str):
        return False
    
    history = load_history()
    
    for i, report in enumerate(history):
        if report.get('id') == report_id:
            history[i]['is_draft'] = False
            history[i]['status'] = 'completed'
            history[i]['pdf_filename'] = pdf_filename
            history[i]['completed_at'] = datetime.now().isoformat()
            
            if save_history(history):
                logger.info(f"Draft {report_id} converted to completed")
                return True
            return False
    
    return False


def get_report_by_id(report_id: str) -> Optional[Dict]:
    """
    Get a specific report by its ID.
    
    Args:
        report_id: The unique report ID.
        
    Returns:
        The report dictionary if found, None otherwise.
    """
    if not report_id or not isinstance(report_id, str):
        return None
    
    history = load_history()
    
    for report in history:
        if report.get('id') == report_id:
            return report
    
    return None


def delete_report(report_id: str) -> bool:
    """
    Delete a report from history.
    
    Args:
        report_id: The unique report ID to delete.
        
    Returns:
        True if deleted successfully, False otherwise.
    """
    if not report_id or not isinstance(report_id, str):
        logger.warning("Cannot delete report: invalid report_id")
        return False
    
    history = load_history()
    
    original_length = len(history)
    history = [r for r in history if r.get('id') != report_id]
    
    if len(history) < original_length:
        if save_history(history):
            logger.info(f"Report {report_id} deleted from history")
            return True
        logger.error(f"Failed to save history after deleting report {report_id}")
        return False
    
    logger.warning(f"Report {report_id} not found in history")
    return False


def get_history_summary() -> List[Dict]:
    """
    Get a summary of all reports (without full form data).
    
    Returns:
        List of report summaries with key fields only.
    """
    history = load_history()
    
    summaries = []
    for report in history:
        summaries.append({
            'id': report.get('id'),
            'created_at': report.get('created_at'),
            'created_at_formatted': report.get('created_at_formatted'),
            'updated_at_formatted': report.get('updated_at_formatted'),
            'event_type': report.get('event_type'),
            'city': report.get('city'),
            'venue_name': report.get('venue_name'),
            'hotel_name': report.get('hotel_name'),
            'hotel2_name': report.get('hotel2_name'),
            'event_start_date': report.get('event_start_date'),
            'event_end_date': report.get('event_end_date'),
            'is_draft': report.get('is_draft', False),
            'status': report.get('status', 'completed'),
        })
    
    return summaries


def clear_all_history() -> bool:
    """
    Clear all history entries.
    
    Returns:
        True if successful, False otherwise.
    """
    result = save_history([])
    if result:
        logger.info("All history cleared")
    else:
        logger.error("Failed to clear history")
    return result
