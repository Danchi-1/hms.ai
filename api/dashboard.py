from flask import Blueprint, jsonify, session
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.models import DatabaseManager

dashboard_bp = Blueprint('dashboard', __name__)
db_manager = DatabaseManager()

@dashboard_bp.route('/<int:user_id>')
def dashboard(user_id):
    try:
        # Security check: Ensure requesting user matches session
        if 'user_id' not in session or session['user_id'] != user_id:
             return jsonify({'error': 'Unauthorized'}), 401

        health_data = db_manager.get_user_health_data(user_id, days=7)

        activity_summary = {}
        if health_data['activity']:
            recent = health_data['activity'][:7]
            activity_summary = {
                'avg_steps': sum(a['total_steps'] for a in recent) / len(recent),
                'avg_calories': sum(a['calories'] for a in recent) / len(recent),
                'avg_active_minutes': sum(a['very_active_minutes'] + a['fairly_active_minutes'] for a in recent) / len(recent)
            }

        sleep_summary = {}
        if health_data['sleep']:
            recent = health_data['sleep'][:7]
            sleep_summary = {
                'avg_sleep_duration': sum(s['total_minutes_asleep'] for s in recent) / len(recent),
                'avg_sleep_efficiency': sum(s['sleep_efficiency'] for s in recent) / len(recent)
            }

        heart_rate_summary = {}
        if health_data['heart_rate']:
            recent = health_data['heart_rate'][-100:]
            heart_rate_summary = {
                'avg_heart_rate': sum(h['heart_rate'] for h in recent) / len(recent),
                'max_heart_rate': max(h['heart_rate'] for h in recent),
                'min_heart_rate': min(h['heart_rate'] for h in recent)
            }

        return jsonify({
            'user_id': user_id,
            'summary': {
                'activity': activity_summary,
                'sleep': sleep_summary,
                'heart_rate': heart_rate_summary
            },
            'raw_data': health_data,
            'last_updated': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
