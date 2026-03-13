from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.models import db, EmergencyContact, limiter
from datetime import datetime
import json
import os
import logging

logger = logging.getLogger(__name__)

emergency_bp = Blueprint('emergency', __name__)

# ── Twilio helper (graceful fallback if not configured) ───────────────────────
def _send_sms(to_number: str, body: str) -> bool:
    """Send SMS via Twilio. Returns True on success, False on failure/unconfigured."""
    sid   = os.getenv('TWILIO_ACCOUNT_SID')
    token = os.getenv('TWILIO_AUTH_TOKEN')
    from_ = os.getenv('TWILIO_PHONE_NUMBER')

    if not all([sid, token, from_]):
        logger.warning(f"[HMS-AI Emergency] Twilio not configured. SMS to {to_number} suppressed.")
        logger.info(f"[HMS-AI Emergency] SMS body: {body}")
        return False

    try:
        from twilio.rest import Client
        client = Client(sid, token)
        client.messages.create(body=body, from_=from_, to=to_number)
        logger.info(f"[HMS-AI Emergency] SMS sent to {to_number}")
        return True
    except Exception as e:
        logger.error(f"[HMS-AI Emergency] Twilio error: {e}")
        return False


def _send_email(to_email: str, subject: str, body: str) -> bool:
    """Placeholder for email alerts. Extend with SendGrid/SES when available."""
    logger.info(f"[HMS-AI Emergency] Email alert → {to_email} | {subject}")
    return False   # Will return True once email service is integrated


# ── Endpoints ─────────────────────────────────────────────────────────────────

@emergency_bp.route('/trigger', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def trigger_emergency():
    """Log an emergency event and return contact list + config for the frontend."""
    try:
        identity = json.loads(get_jwt_identity())
        user_id  = identity['id']
        username = identity['username']

        data       = request.get_json() or {}
        vitals     = data.get('vitals', {})
        trigger    = data.get('trigger_source', 'unknown')  # 'manual' | 'vitals' | 'fall' | 'ml'
        location   = data.get('location', {})

        contacts = EmergencyContact.query.filter_by(user_id=user_id).order_by(EmergencyContact.priority).all()

        logger.warning(
            f"[HMS-AI] EMERGENCY triggered by {username} | source={trigger} | vitals={vitals}"
        )

        emergency_number = os.getenv('EMERGENCY_NUMBER', '767')
        countdown        = int(os.getenv('EMERGENCY_COUNTDOWN_SECONDS', 15))

        return jsonify({
            'triggered': True,
            'trigger_source': trigger,
            'user': username,
            'contacts': [c.to_dict() for c in contacts],
            'emergency_number': emergency_number,
            'countdown_seconds': countdown,
            'vitals': vitals,
            'location': location,
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Emergency trigger error: {e}")
        return jsonify({'error': str(e)}), 500


@emergency_bp.route('/alert', methods=['POST'])
@jwt_required()
@limiter.limit("10 per minute")
def send_alert():
    """Send SMS + email to all emergency contacts for this user."""
    try:
        identity = json.loads(get_jwt_identity())
        user_id  = identity['id']
        username = identity['username']

        data         = request.get_json() or {}
        vitals       = data.get('vitals', {})
        location     = data.get('location', {})
        anomaly_type = data.get('anomaly_type', 'Unknown emergency')

        contacts = EmergencyContact.query.filter_by(user_id=user_id).order_by(EmergencyContact.priority).all()

        if not contacts:
            return jsonify({'message': 'No emergency contacts configured', 'alerted': 0}), 200

        maps_link = ''
        if location.get('latitude') and location.get('longitude'):
            maps_link = f"\nLocation: https://maps.google.com/?q={location['latitude']},{location['longitude']}"

        hr  = vitals.get('heart_rate', 'N/A')
        spo = vitals.get('spo2', 'N/A')
        ts  = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')

        sms_body = (
            f"🚨 HMS-AI EMERGENCY ALERT 🚨\n"
            f"{username} may need immediate help.\n"
            f"Anomaly: {anomaly_type}\n"
            f"Heart Rate: {hr} BPM | SpO2: {spo}%\n"
            f"Time: {ts}{maps_link}\n"
            f"— HMS-AI Health Monitor"
        )

        alerted = 0
        for contact in contacts:
            sms_ok = _send_sms(contact.phone_number, sms_body)
            _send_email(
                to_email=f"{contact.name}@placeholder.com",  # replace with stored email when schema expanded
                subject=f"🚨 Emergency Alert for {username}",
                body=sms_body
            )
            if sms_ok:
                alerted += 1

        return jsonify({
            'message': f'Alerts dispatched to {len(contacts)} contact(s)',
            'alerted_via_sms': alerted,
            'fallback': alerted < len(contacts),
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    except Exception as e:
        logger.error(f"Emergency alert error: {e}")
        return jsonify({'error': str(e)}), 500


@emergency_bp.route('/contacts', methods=['GET'])
@jwt_required()
def get_contacts():
    try:
        identity = json.loads(get_jwt_identity())
        contacts = EmergencyContact.query.filter_by(user_id=identity['id']).order_by(EmergencyContact.priority).all()
        return jsonify([c.to_dict() for c in contacts]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@emergency_bp.route('/contacts', methods=['POST'])
@jwt_required()
@limiter.limit("20 per minute")
def add_contact():
    try:
        identity = json.loads(get_jwt_identity())
        user_id  = identity['id']

        # Enforce max 5 contacts
        count = EmergencyContact.query.filter_by(user_id=user_id).count()
        if count >= 5:
            return jsonify({'error': 'Maximum 5 emergency contacts allowed'}), 400

        data = request.get_json() or {}
        required = ['name', 'phone_number', 'relationship']
        if not all(k in data for k in required):
            return jsonify({'error': f'Missing fields: {required}'}), 400

        contact = EmergencyContact(
            user_id=user_id,
            name=data['name'].strip(),
            phone_number=data['phone_number'].strip(),
            relationship=data['relationship'].strip(),
            priority=data.get('priority', count + 1)
        )
        db.session.add(contact)
        db.session.commit()
        return jsonify(contact.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@emergency_bp.route('/contacts/<int:contact_id>', methods=['DELETE'])
@jwt_required()
def remove_contact(contact_id):
    try:
        identity = json.loads(get_jwt_identity())
        contact = EmergencyContact.query.filter_by(id=contact_id, user_id=identity['id']).first()
        if not contact:
            return jsonify({'error': 'Contact not found'}), 404
        db.session.delete(contact)
        db.session.commit()
        return jsonify({'message': 'Contact removed'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
