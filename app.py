import os
import logging
from flask import Flask, render_template, request, session, redirect, url_for, send_file, jsonify
from docx_generator import create_report

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from services.watchdog import watchdog, monitor_function
from services.flask_middleware import init_watchdog

from pdf_generator import create_pdf_report
from services.maps_api import fetch_hotel_data, fetch_venue_data, search_hotels, search_venues
from services.ai_helper import ai_assist_hotel, ai_assist_venue, is_ai_available
from services.security_intelligence import (
    generate_security_brief_hotel, 
    generate_security_brief_venue,
    is_security_ai_available
)
from services.history import (
    add_report_to_history,
    get_report_by_id,
    get_history_summary,
    delete_report as delete_history_report,
    update_draft,
    convert_draft_to_completed
)
from services.form_utils import (
    SECURITY_ITEMS,
    get_default_form_data,
    get_empty_hotel_data,
    get_empty_hotel_ai_data,
    get_empty_venue_data,
    get_empty_venue_ai_data,
    build_name_address_fields,
    build_security_data,
    generate_safe_filename
)
from services.security_questionnaire import (
    get_empty_questionnaire,
    get_questionnaire,
    get_questionnaire_by_id,
    save_questionnaire,
    generate_venue_id
)
from docx_generator import create_security_questionnaire_docx
from services.security_brief import get_security_brief_service
from services.riskbrief import risk_bp
from services.mediastack import mediastack_bp

app = Flask(__name__)
app.secret_key = os.environ.get('SESSION_SECRET', os.environ.get('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production'))

init_watchdog(app)

app.register_blueprint(risk_bp, url_prefix='/api')
app.register_blueprint(mediastack_bp, url_prefix='/api')


@app.route('/api/watchdog/log', methods=['POST'])
def watchdog_client_log():
    """Receive logs from the frontend watchdog client."""
    try:
        data = request.get_json(silent=True) or {}
        logs = data.get('logs', [])
        
        if not isinstance(logs, list) or len(logs) > 100:
            return jsonify({'success': False, 'error': 'Invalid payload'})
        
        ALLOWED_EVENTS = {
            'CLIENT_INIT', 'JS_ERROR', 'PROMISE_REJECTION', 'CONSOLE_ERROR', 
            'CONSOLE_WARN', 'USER_CLICK', 'FORM_SUBMIT', 'NAVIGATION',
            'PAGE_LOAD', 'SLOW_PAGE_LOAD', 'SLOW_FETCH', 'SLOW_RESOURCE',
            'LONG_TASK', 'NETWORK_ERROR', 'FETCH_ERROR', 'PAGE_UNLOAD', 'CUSTOM_EVENT'
        }
        
        def sanitize_string(val, max_len=500):
            if not isinstance(val, str):
                return str(val)[:max_len] if val else ''
            return val[:max_len].replace('\n', ' ').replace('\r', '')
        
        for log_entry in logs[:50]:
            if not isinstance(log_entry, dict):
                continue
                
            event_type = sanitize_string(log_entry.get('eventType', 'CLIENT_EVENT'), 50)
            if event_type not in ALLOWED_EVENTS:
                event_type = 'UNKNOWN_CLIENT_EVENT'
            
            message = sanitize_string(log_entry.get('message', ''), 500)
            
            log_data = {
                'client_ip': request.remote_addr,
                'server_timestamp': __import__('datetime').datetime.now().isoformat()
            }
            
            client_data = log_entry.get('data', {})
            if isinstance(client_data, dict):
                for k, v in list(client_data.items())[:10]:
                    log_data[f'client_{sanitize_string(k, 30)}'] = sanitize_string(str(v), 200)
            
            if event_type in ['JS_ERROR', 'PROMISE_REJECTION', 'CONSOLE_ERROR', 'NETWORK_ERROR', 'FETCH_ERROR']:
                watchdog.log_event(f'CLIENT:{event_type}', message, 'ERROR', log_data)
            elif event_type in ['CONSOLE_WARN', 'SLOW_PAGE_LOAD', 'SLOW_FETCH', 'SLOW_RESOURCE', 'LONG_TASK']:
                watchdog.log_event(f'CLIENT:{event_type}', message, 'WARNING', log_data)
            else:
                watchdog.log_user_action(event_type, message, extra_data=log_data)
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f'Watchdog log error: {str(e)}')
        return jsonify({'success': False, 'error': 'Internal error'})


@app.route('/api/watchdog/stats', methods=['GET'])
def watchdog_stats():
    """Get current watchdog performance statistics."""
    try:
        stats = watchdog.get_performance_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/security-intel', methods=['GET'])
def api_security_intel():
    """
    Get security intelligence for a city/country.
    
    Query params:
        city: City name (required)
        country: Country name (required)
        offline: Use only cached data (optional, default false)
    
    Returns JSON with homicides_30d, demonstrations_14d, risk_assessment
    """
    try:
        city = request.args.get('city', '').strip()
        country = request.args.get('country', '').strip()
        offline = request.args.get('offline', 'false').lower() == 'true'
        
        if not city or not country:
            return jsonify({
                'success': False,
                'error': 'City and country are required',
                'meta': {'error': True}
            }), 400
        
        from services.security_intelligence_v2 import get_full_security_intel
        
        result = get_full_security_intel(
            city=city,
            country=country,
            use_cache=True,
            offline_mode=offline
        )
        
        return jsonify({
            'success': True,
            **result
        })
        
    except Exception as e:
        logger.error(f'Security intel error: {e}', exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'meta': {
                'error': True,
                'message': 'Failed to fetch security intelligence'
            }
        }), 500


@app.route('/search_hotels', methods=['POST'])
def search_hotels_route():
    """Search for hotels by name/chain, city and country."""
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        city = data.get('city', '').strip()
        country = data.get('country', '').strip()
        
        if not query:
            return jsonify({'success': True, 'results': []})
        
        results = search_hotels(query, city, country=country, limit=10)
        return jsonify({'success': True, 'results': results})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e), 'results': []})


@app.route('/search_venues', methods=['POST'])
def search_venues_route():
    """Search for venues by name and city."""
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        city = data.get('city', '').strip()
        
        if not query:
            return jsonify({'success': True, 'results': []})
        
        results = search_venues(query, city, limit=10)
        return jsonify({'success': True, 'results': results})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e), 'results': []})


@app.route('/fetch_place_photo', methods=['POST'])
def fetch_place_photo_route():
    """Fetch a photo for a hotel or venue using placeholder images."""
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        place_type = data.get('type', 'hotel')
        
        if not query:
            return jsonify({'success': False, 'error': 'No query provided'})
        
        import hashlib
        seed = hashlib.md5(query.encode()).hexdigest()[:10]
        
        if 'hotel' in place_type.lower():
            photo_url = f"https://source.unsplash.com/800x500/?hotel,building,{seed}"
        elif 'arena' in place_type.lower() or 'venue' in place_type.lower():
            photo_url = f"https://source.unsplash.com/800x500/?arena,stadium,concert,{seed}"
        else:
            photo_url = f"https://source.unsplash.com/800x500/?building,architecture,{seed}"
        
        return jsonify({
            'success': True,
            'photo_url': photo_url,
            'thumbnail_url': photo_url,
            'source': 'unsplash'
        })
        
    except Exception as e:
        logger.error(f'Error fetching place photo: {e}')
        return jsonify({'success': False, 'error': str(e)})


@app.route('/search_cities', methods=['POST'])
def search_cities_route():
    """Search for cities by name using Photon geocoding API."""
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        country = data.get('country', '').strip()
        
        if not query or len(query) < 2:
            return jsonify({'success': True, 'results': []})
        
        import requests
        import unicodedata
        from urllib.parse import quote
        
        def normalize_str(s):
            return unicodedata.normalize('NFD', s.lower()).encode('ascii', 'ignore').decode('ascii')
        
        search_query = query
        if country:
            search_query = f"{query}, {country}"
        
        url = f"https://photon.komoot.io/api/?q={quote(search_query)}&limit=15&lang=fr"
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                results = []
                seen = set()
                
                for feature in data.get('features', []):
                    props = feature.get('properties', {})
                    osm_type = props.get('osm_value', '')
                    
                    if osm_type not in ['city', 'town', 'village', 'municipality', 'suburb', 'district']:
                        place_type = props.get('type', '')
                        if place_type not in ['city', 'town', 'village', 'locality']:
                            continue
                    
                    city_name = props.get('name', '')
                    if not city_name:
                        continue
                    
                    city_country = props.get('country', '')
                    state = props.get('state', '')
                    
                    display = city_name
                    if state and state != city_name:
                        display = f"{city_name}, {state}"
                    if city_country:
                        display = f"{display}, {city_country}"
                    
                    key = normalize_str(display)
                    if key in seen:
                        continue
                    seen.add(key)
                    
                    coords = feature.get('geometry', {}).get('coordinates', [])
                    
                    results.append({
                        'name': city_name,
                        'display': display,
                        'country': city_country,
                        'state': state,
                        'lat': coords[1] if len(coords) > 1 else None,
                        'lon': coords[0] if len(coords) > 0 else None
                    })
                    
                    if len(results) >= 8:
                        break
                
                return jsonify({'success': True, 'results': results})
        
        except Exception as e:
            logger.warning(f"City search error: {e}")
        
        return jsonify({'success': True, 'results': []})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e), 'results': []})


@app.route('/ai_assist_hotel', methods=['POST'])
def ai_assist_hotel_route():
    empty_data = get_empty_hotel_ai_data()
    
    try:
        data = request.get_json() or {}
        hotel_name = data.get('hotel_name', '').strip()
        hotel_address = data.get('hotel_address', '').strip()
        
        if not hotel_name and not hotel_address:
            return jsonify({
                'success': False,
                'message': 'Please enter a hotel name or address first.',
                'data': empty_data
            })
        
        venue_address = session.get('form_data', {}).get('venue_address', '')
        result = ai_assist_hotel(hotel_name, hotel_address, venue_address)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'AI assistant error: {str(e)}',
            'data': empty_data
        })


@app.route('/ai_assist_venue', methods=['POST'])
def ai_assist_venue_route():
    empty_data = get_empty_venue_ai_data()
    
    try:
        data = request.get_json() or {}
        venue_name = data.get('venue_name', '').strip()
        venue_address = data.get('venue_address', '').strip()
        
        if not venue_name and not venue_address:
            return jsonify({
                'success': False,
                'message': 'Please enter a venue name or address first.',
                'data': empty_data
            })
        
        result = ai_assist_venue(venue_name, venue_address)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'AI assistant error: {str(e)}',
            'data': empty_data
        })


@app.route('/security_brief_hotel', methods=['POST'])
def security_brief_hotel_route():
    """
    Generate a security intelligence brief for a hotel.
    
    This endpoint receives hotel information and returns a comprehensive
    security-oriented analysis with risks, recommendations, and action items.
    """
    try:
        data = request.get_json() or {}
        
        brief_data = {
            'hotel_name': data.get('hotel_name', '').strip(),
            'hotel_address': data.get('hotel_address', '').strip(),
            'city': data.get('city', '').strip(),
            'event_date': data.get('event_date', '').strip(),
            'event_type': data.get('event_type', '').strip(),
            'additional_context': data.get('additional_context', '').strip()
        }
        
        if not brief_data['hotel_name'] and not brief_data['hotel_address']:
            return jsonify({
                'success': False,
                'message': 'Please enter a hotel name or address first.',
                'brief': ''
            })
        
        result = generate_security_brief_hotel(brief_data)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Security brief error: {str(e)}',
            'brief': ''
        })


@app.route('/security_brief_venue', methods=['POST'])
def security_brief_venue_route():
    """
    Generate a security intelligence brief for a venue.
    
    This endpoint receives venue information and returns a comprehensive
    security-oriented analysis with risks, recommendations, and action items.
    """
    try:
        data = request.get_json() or {}
        
        brief_data = {
            'venue_name': data.get('venue_name', '').strip(),
            'venue_address': data.get('venue_address', '').strip(),
            'city': data.get('city', '').strip(),
            'event_date': data.get('event_date', '').strip(),
            'event_type': data.get('event_type', '').strip(),
            'expected_capacity': data.get('expected_capacity', '').strip(),
            'additional_context': data.get('additional_context', '').strip()
        }
        
        if not brief_data['venue_name'] and not brief_data['venue_address']:
            return jsonify({
                'success': False,
                'message': 'Please enter a venue name or address first.',
                'brief': ''
            })
        
        result = generate_security_brief_venue(brief_data)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Security brief error: {str(e)}',
            'brief': ''
        })


@app.route('/security-questionnaire', methods=['GET', 'POST'])
def security_questionnaire():
    form_data = session.get('form_data', get_default_form_data())
    venue_name = form_data.get('venue_name', '').strip()
    venue_address = form_data.get('venue_address', '').strip()
    city = form_data.get('event_city', '').strip()
    country = form_data.get('event_country', '').strip()
    
    if not venue_name:
        return redirect(url_for('index'))
    
    venue_id = generate_venue_id(venue_name, venue_address)
    existing = get_questionnaire(venue_name, venue_address)
    is_edit = existing is not None
    
    if request.method == 'POST':
        data = {
            'external_threat_description': request.form.get('external_threat_description', ''),
            'external_threat_meeting_point': request.form.get('external_threat_meeting_point', ''),
            'fire_gathering_points': request.form.get('fire_gathering_points', ''),
            'screening_walk_through': 'screening_walk_through' in request.form,
            'screening_handheld': 'screening_handheld' in request.form,
            'screening_pat_down': 'screening_pat_down' in request.form,
            'screening_bag_checks': 'screening_bag_checks' in request.form,
            'missing_child_protocol': request.form.get('missing_child_protocol', ''),
            'missing_child_notes': request.form.get('missing_child_notes', ''),
            'backstage_id_required': 'backstage_id_required' in request.form,
            'backstage_escort_required': 'backstage_escort_required' in request.form,
            'backstage_sign_in_required': 'backstage_sign_in_required' in request.form,
            'backstage_notes': request.form.get('backstage_notes', ''),
            'security_company_name': request.form.get('security_company_name', ''),
            'security_supervisors': int(request.form.get('security_supervisors', 0) or 0),
            'security_guards': int(request.form.get('security_guards', 0) or 0),
            'security_traffic_management': int(request.form.get('security_traffic_management', 0) or 0),
            'security_ticket_checkers': int(request.form.get('security_ticket_checkers', 0) or 0),
            'security_ushers': int(request.form.get('security_ushers', 0) or 0),
            'security_medics': int(request.form.get('security_medics', 0) or 0),
            'security_other': int(request.form.get('security_other', 0) or 0),
            'security_other_description': request.form.get('security_other_description', ''),
            'general_cctv_operational': request.form.get('general_cctv_operational', ''),
            'general_lighting_adequate': request.form.get('general_lighting_adequate', ''),
            'general_emergency_exits_clear': request.form.get('general_emergency_exits_clear', ''),
            'general_fire_extinguishers': request.form.get('general_fire_extinguishers', ''),
            'general_first_aid_kits': request.form.get('general_first_aid_kits', ''),
            'general_communication_radios': request.form.get('general_communication_radios', ''),
            'crowd_capacity_limits': request.form.get('crowd_capacity_limits', ''),
            'crowd_barrier_placement': request.form.get('crowd_barrier_placement', ''),
            'crowd_queuing_system': request.form.get('crowd_queuing_system', ''),
            'crowd_vip_separate_access': request.form.get('crowd_vip_separate_access', ''),
            'crowd_disabled_access': request.form.get('crowd_disabled_access', ''),
            'medical_ambulance_onsite': request.form.get('medical_ambulance_onsite', ''),
            'medical_paramedics_count': int(request.form.get('medical_paramedics_count', 0) or 0),
            'medical_first_aiders_count': int(request.form.get('medical_first_aiders_count', 0) or 0),
            'medical_hospital_distance': request.form.get('medical_hospital_distance', ''),
            'medical_policy_notes': request.form.get('medical_policy_notes', ''),
            'additional_notes': request.form.get('additional_notes', '')
        }
        
        result = save_questionnaire(venue_name, venue_address, city, country, data)
        if result:
            return render_template('security_questionnaire.html',
                venue_name=venue_name,
                venue_address=venue_address,
                city=city,
                country=country,
                venue_id=venue_id,
                data=data,
                is_edit=True,
                message='Questionnaire saved successfully!',
                message_type='success')
        else:
            return render_template('security_questionnaire.html',
                venue_name=venue_name,
                venue_address=venue_address,
                city=city,
                country=country,
                venue_id=venue_id,
                data=data,
                is_edit=is_edit,
                message='Error saving questionnaire.',
                message_type='error')
    
    data = existing.get('data', get_empty_questionnaire()) if existing else get_empty_questionnaire()
    
    return render_template('security_questionnaire.html',
        venue_name=venue_name,
        venue_address=venue_address,
        city=city,
        country=country,
        venue_id=venue_id,
        data=data,
        is_edit=is_edit)


@app.route('/security-questionnaire/export/<venue_id>')
def export_security_questionnaire(venue_id):
    questionnaire = get_questionnaire_by_id(venue_id)
    if not questionnaire:
        return redirect(url_for('index'))
    
    form_data = session.get('form_data', get_default_form_data())
    event_date = form_data.get('event_start_date', '')
    
    docx_buffer = create_security_questionnaire_docx(questionnaire, event_date)
    
    venue_name = questionnaire.get('venue_name', 'venue')
    safe_name = generate_safe_filename(f"Security_Questionnaire_{venue_name}")
    filename = f"{safe_name}.docx"
    
    return send_file(
        docx_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )


@app.route('/save_form', methods=['POST'])
def save_form_ajax():
    try:
        data = request.get_json() or {}
        
        if 'form_data' not in session:
            session['form_data'] = get_default_form_data()
        
        form_data = session['form_data'].copy()
        
        for key, value in data.items():
            if key in form_data:
                form_data[key] = value
        
        session['form_data'] = form_data
        session.modified = True
        
        return jsonify({'success': True, 'message': 'Form data saved'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        if session.get('loading_from_history'):
            session.pop('loading_from_history', None)
        elif session.get('preserve_form_data'):
            session.pop('preserve_form_data', None)
        elif 'form_data' not in session:
            session['form_data'] = get_default_form_data()
            session.pop('current_draft_id', None)
        session.modified = True
    
    if 'form_data' not in session:
        session['form_data'] = get_default_form_data()
    
    if request.method == 'POST':
        action = request.form.get('action', '')
        
        form_data = session['form_data'].copy()
        for key in form_data.keys():
            if key in request.form:
                form_data[key] = request.form.get(key, '')
        
        form_data['has_two_hotels'] = request.form.get('has_two_hotels') == 'true'
        build_name_address_fields(form_data)
        
        session['form_data'] = form_data
        session.modified = True
        
        if action == 'add_hotel':
            form_data['has_two_hotels'] = True
            session['form_data'] = form_data
            session.modified = True
            return redirect(url_for('index'))
        
        elif action == 'remove_hotel':
            form_data['has_two_hotels'] = False
            for key in list(form_data.keys()):
                if key.startswith('hotel2_'):
                    form_data[key] = ''
            session['form_data'] = form_data
            session.modified = True
            return redirect(url_for('index'))
        
        session['form_data'] = form_data
        session.modified = True
    
    has_api_key = bool(os.environ.get('GOOGLE_MAPS_API_KEY'))
    ai_available = is_ai_available()
    security_ai_available = is_security_ai_available()
    current_draft_id = session.get('current_draft_id')
    return render_template('index.html', 
                         form_data=session['form_data'], 
                         has_api_key=has_api_key,
                         ai_available=ai_available,
                         security_ai_available=security_ai_available,
                         security_items=SECURITY_ITEMS,
                         current_draft_id=current_draft_id)


@app.route('/generate', methods=['POST'])
def generate_report():
    """Generate and download a Word document report."""
    try:
        form_data = get_default_form_data()
        session_data = session.get('form_data', {})
        form_data.update(session_data)
        
        for key in request.form.keys():
            if key in form_data:
                form_data[key] = request.form.get(key, '')
        
        form_data['has_two_hotels'] = 'has_two_hotels' in request.form or request.form.get('has_two_hotels') == 'true'
        build_name_address_fields(form_data)
        
        session['form_data'] = form_data
        session.modified = True
        
        security_data = build_security_data(form_data)
        doc_io = create_report(form_data, security_data)
        filename = generate_safe_filename(form_data.get('venue_name', 'Report'), 'docx')
        
        current_draft_id = session.get('current_draft_id')
        if current_draft_id:
            update_draft(current_draft_id, form_data, security_data)
            convert_draft_to_completed(current_draft_id, filename)
            session.pop('current_draft_id', None)
        
        session['form_data'] = form_data
        session.modified = True
        
        return send_file(
            doc_io,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f'Error generating Word document: {str(e)}', exc_info=True)
        return render_template('index.html',
                             form_data=session.get('form_data', get_default_form_data()),
                             has_api_key=bool(os.environ.get('GOOGLE_MAPS_API_KEY')),
                             ai_available=is_ai_available(),
                             security_ai_available=is_security_ai_available(),
                             security_items=SECURITY_ITEMS,
                             error_message=f'Error generating Word document: {str(e)}'), 500


@app.route('/generate_pdf', methods=['POST'])
def generate_pdf_report():
    """Generate and download a PDF report, save to history, and reset form."""
    try:
        form_data = get_default_form_data()
        session_data = session.get('form_data', {})
        form_data.update(session_data)
        
        for key in request.form.keys():
            if key in form_data:
                form_data[key] = request.form.get(key, '')
        
        form_data['has_two_hotels'] = 'has_two_hotels' in request.form or request.form.get('has_two_hotels') == 'true'
        build_name_address_fields(form_data)
        
        security_data = build_security_data(form_data)
        filename = generate_safe_filename(form_data.get('venue_name', 'Report'), 'pdf')
        
        current_draft_id = session.get('current_draft_id')
        if current_draft_id:
            update_draft(current_draft_id, form_data, security_data)
            convert_draft_to_completed(current_draft_id, filename)
            session.pop('current_draft_id', None)
        else:
            add_report_to_history(form_data, security_data, filename)
        
        pdf_io = create_pdf_report(form_data, security_data)
        
        session['form_data'] = form_data
        session.modified = True
        
        return send_file(
            pdf_io,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f'Error generating PDF report: {str(e)}', exc_info=True)
        return render_template('index.html',
                             form_data=session.get('form_data', get_default_form_data()),
                             has_api_key=bool(os.environ.get('GOOGLE_MAPS_API_KEY')),
                             ai_available=is_ai_available(),
                             security_ai_available=is_security_ai_available(),
                             security_items=SECURITY_ITEMS,
                             error_message=f'Error generating PDF report: {str(e)}'), 500


@app.route('/new', methods=['POST'])
def new_report():
    session['form_data'] = get_default_form_data()
    session.pop('current_draft_id', None)
    session.modified = True
    return redirect(url_for('index'))


@app.route('/save_draft', methods=['POST'])
def save_draft():
    """Save current form as a draft in history."""
    try:
        form_data = get_default_form_data()
        session_data = session.get('form_data', {})
        form_data.update(session_data)
        
        logger.info(f"[SAVE_DRAFT] Received form keys: {list(request.form.keys())}")
        
        for key in request.form.keys():
            form_data[key] = request.form.get(key, '')
        
        logger.info(f"[SAVE_DRAFT] event_start_date={form_data.get('event_start_date')}, event_country={form_data.get('event_country')}, hotel1_name={form_data.get('hotel1_name')}")
        
        form_data['has_two_hotels'] = 'has_two_hotels' in request.form or request.form.get('has_two_hotels') == 'true'
        build_name_address_fields(form_data)
        
        session['form_data'] = form_data
        session.modified = True
        
        security_data = build_security_data(form_data)
        
        current_draft_id = session.get('current_draft_id')
        
        if current_draft_id:
            success = update_draft(current_draft_id, form_data, security_data)
            if success:
                return jsonify({
                    'success': True, 
                    'message': 'Brouillon mis à jour',
                    'draft_id': current_draft_id
                })
        
        draft_id = add_report_to_history(form_data, security_data, is_draft=True)
        
        if draft_id:
            session['current_draft_id'] = draft_id
            session.modified = True
            return jsonify({
                'success': True, 
                'message': 'Brouillon sauvegardé',
                'draft_id': draft_id
            })
        
        return jsonify({'success': False, 'message': 'Erreur lors de la sauvegarde'})
    
    except Exception as e:
        logger.error(f'Error saving draft: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})


@app.route('/history')
def history_page():
    """Display the history of generated reports."""
    try:
        reports = get_history_summary()
        return render_template('history.html', reports=reports)
    except Exception as e:
        logger.error(f'Error loading history: {str(e)}', exc_info=True)
        return render_template('history.html', reports=[], error_message=f'Error loading history: {str(e)}'), 500


@app.route('/history/load/<report_id>')
def load_from_history(report_id):
    """Load a report from history into the form."""
    try:
        report = get_report_by_id(report_id)
        
        if report and 'form_data' in report:
            session['form_data'] = report['form_data']
            session['loading_from_history'] = True
            if report.get('is_draft'):
                session['current_draft_id'] = report_id
            else:
                session.pop('current_draft_id', None)
            session.modified = True
            return redirect(url_for('index'))
        
        return redirect(url_for('history_page'))
    except Exception as e:
        logger.error(f'Error loading report: {str(e)}', exc_info=True)
        try:
            reports = get_history_summary()
        except Exception:
            reports = []
        return render_template('history.html', reports=reports, error_message=f'Error loading report: {str(e)}'), 500


@app.route('/history/delete/<report_id>', methods=['POST'])
def delete_from_history(report_id):
    """Delete a report from history."""
    try:
        delete_history_report(report_id)
        return redirect(url_for('history_page'))
    except Exception as e:
        logger.error(f'Error deleting report: {str(e)}', exc_info=True)
        try:
            reports = get_history_summary()
        except Exception:
            reports = []
        return render_template('history.html', reports=reports, error_message=f'Error deleting report: {str(e)}'), 500


@app.route('/api/history', methods=['GET'])
def get_history_api():
    """API endpoint to get history summary."""
    try:
        reports = get_history_summary()
        return jsonify({'success': True, 'reports': reports})
    except Exception as e:
        logger.error(f'Error fetching history API: {str(e)}', exc_info=True)
        return jsonify({'success': False, 'message': f'Error fetching history: {str(e)}', 'reports': []}), 500


@app.route('/security-brief')
def security_brief_page():
    """Render the City Security Brief page."""
    return render_template('security_brief.html')


@app.route('/api/security-brief', methods=['POST'])
def generate_security_brief():
    """Generate a security brief for a city."""
    try:
        data = request.get_json() or {}
        city = data.get('city', '').strip()
        country = data.get('country', '').strip()
        address = data.get('address', '').strip() or None
        start_date = data.get('start_date', '').strip() or None
        end_date = data.get('end_date', '').strip() or None
        
        if not city or not country:
            return jsonify({
                'success': False,
                'error': 'City and country are required'
            }), 400
        
        service = get_security_brief_service()
        result = service.generate_brief(city, country, address, start_date=start_date, end_date=end_date)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'Error generating security brief: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Failed to generate brief: {str(e)}'
        }), 500


@app.route('/api/security-brief/refresh', methods=['POST'])
def refresh_security_brief():
    """Force refresh a security brief (bypass cache)."""
    try:
        data = request.get_json() or {}
        city = data.get('city', '').strip()
        country = data.get('country', '').strip()
        address = data.get('address', '').strip() or None
        start_date = data.get('start_date', '').strip() or None
        end_date = data.get('end_date', '').strip() or None
        
        if not city or not country:
            return jsonify({
                'success': False,
                'error': 'City and country are required'
            }), 400
        
        service = get_security_brief_service()
        service.invalidate_cache(city, country, address)
        result = service.generate_brief(city, country, address, use_cache=False, start_date=start_date, end_date=end_date)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f'Error refreshing security brief: {str(e)}', exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Failed to refresh brief: {str(e)}'
        }), 500


@app.route('/health')
def healthcheck():
    """Health check endpoint for monitoring and load balancers."""
    return jsonify({
        'status': 'healthy',
        'app': 'Response Report Generator',
        'version': '1.0.0'
    })


@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors."""
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Resource not found'}), 404
    return render_template('error.html', 
                          error_code=404, 
                          error_message='Page not found'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f'Internal server error: {error}', exc_info=True)
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Internal server error'}), 500
    return render_template('error.html',
                          error_code=500,
                          error_message='An unexpected error occurred'), 500


if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    app.run(host=host, port=port, debug=True)
