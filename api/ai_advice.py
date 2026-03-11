from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import google.generativeai as genai
import json
import logging
import time
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ai_bp = Blueprint('ai', __name__)

# Simple in-memory cache to prevent Gemini API quota exhaustion
# Structure: { user_id: { 'timestamp': float, 'data': dict } }
advice_cache = {}
CACHE_TTL = 1800  # 30 minutes in seconds

# Configure Gemini
API_KEY = os.getenv('GEMINI_API_KEY')
if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    logger.warning("GEMINI_API_KEY not found in environment variables. AI features will be disabled.")

# STRICT SYSTEM PROMPT - DO NOT MODIFY WITHOUT MEDICAL REVIEW
SYSTEM_PROMPT = """
ROLE: Clinical Decision Support System (CDSS) Advisory Layer.
You are an AI assistant analyzing user health telemetry.
 You are NOT a doctor. You CANNOT diagnose.

INPUT DATA:
- User Heart Rate (BPM)
- SpO2 Levels (%)
- Activity/Steps
- Sleep Data
- ML Risk Prediction (Low/Medium/High)

OBJECTIVE:
Provide conservative, risk-aware health context and lifestyle advice based on the data.
Identify trends and potential concerns.
Escalate to human medical professionals if data indicates risk or is abnormal.

CONSTRAINTS (MANDATORY):
1. NEVER output a definitive medical diagnosis (e.g., "You have atrial fibrillation").
2. NEVER prescribe medication or specific dosages.
3. ALWAYS use probabilistic or observational language (e.g., "This may indicate...", "Levels appear elevated...").
4. IF ML Risk is HIGH or data is critical (e.g., SpO2 < 90, HR > 120 resting):
   - You MUST include a strong escalation notice.
   - You MUST advise seeking medical attention.
5. IF ML Risk is MEDIUM:
   - Advise monitoring and potential consultation.
6. IF Data is missing or insufficient:
   - State "Insufficient data to provide analysis."

OUTPUT FORMAT:
Return ONLY valid JSON. No markdown formatting. No conversational filler outside the JSON.
Structure:
{
  "summary": "1-2 sentence overview of current health status.",
  "observations": ["Bullet point 1 about specific metric", "Bullet point 2"],
  "risk_interpretation": "Explanation of the risk level context.",
  "recommended_actions": ["Actionable advice 1", "Actionable advice 2"],
  "escalation_notice": "Urgent warning if applicable, or null/empty string if normal."
}

TONE: Professional, supportive, objective, conservative.
"""

def get_gemini_model():
    if not API_KEY:
        return None
    
    # Safety settings to block harmful content
    safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_MEDIUM_AND_ABOVE"
        },
    ]

    return genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        safety_settings=safety_settings,
        system_instruction=SYSTEM_PROMPT,
        generation_config={"response_mime_type": "application/json"}
    )

@ai_bp.route('/health-advice', methods=['POST'])
@jwt_required()
def get_health_advice():
    # 1. Key Check
    if not API_KEY:
        return jsonify({
            'summary': 'AI Service Unavailable',
            'observations': ['System configuration incomplete.'],
            'risk_interpretation': 'N/A',
            'recommended_actions': [],
            'escalation_notice': None
        })

    try:
        user_id = json.loads(get_jwt_identity())['id']
        
        # 3. Check Cache First (Prevent API looping/exhaustion)
        current_time = time.time()
        if user_id in advice_cache:
            cached = advice_cache[user_id]
            if current_time - cached['timestamp'] < CACHE_TTL:
                logger.info(f"Returning cached AI advice for user {user_id}")
                return jsonify(cached['data'])

        data = request.get_json()
        
        # 3. Construct Context for LLM
        metrics = data.get('metrics', {})
        risk_level = data.get('risk_level', 'Unknown')
        
        user_context_str = f"""
        Packet Timestamp: {metrics.get('timestamp', 'Now')}
        Heart Rate: {metrics.get('heart_rate', 'N/A')} BPM
        SpO2: {metrics.get('spo2', 'N/A')}%
        Steps: {metrics.get('steps', 'N/A')}
        Sleep Score: {metrics.get('sleep_score', 'N/A')}
        
        CURRENT ML RISK ASSESSMENT: {risk_level}
        """

        # 4. Call Gemini
        model = get_gemini_model()
        response = model.generate_content(user_context_str)
        
        # 5. Native JSON Parsing
        try:
            # The model is configured to return strict JSON strings
            advice_json = json.loads(response.text)
            
            # 6. Forced Safety Override (Redundancy)
            # If metrics are critically dangerous, force escalation even if LLM missed it
            hr = metrics.get('heart_rate', 0)
            spo2 = metrics.get('spo2', 100)
            
            critical_condition = False
            if isinstance(hr, (int, float)) and (hr > 130 or hr < 40):
                critical_condition = True
            if isinstance(spo2, (int, float)) and spo2 < 90:
                critical_condition = True
                
            if critical_condition or risk_level == "High":
                if not advice_json.get('escalation_notice'):
                    advice_json['escalation_notice'] = "CRITICAL: Vitals indicate potential medical emergency. Seek help immediately."
            
            # Save to cache before returning
            advice_cache[user_id] = {
                'timestamp': current_time,
                'data': advice_json
            }
            return jsonify(advice_json)

        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response: {response.text}")
            fallback = {
                "summary": "Health data analyzed.",
                "observations": ["Complex patterns detected."],
                "risk_interpretation": "Please review your vitals manually.",
                "recommended_actions": ["Consult healthcare provider if feeling unwell."],
                "escalation_notice": "Error parsing detailed advice."
            }
            return jsonify(fallback)

    except Exception as e:
        logger.error(f"AI Advisor Error (Rate Limit or Connection): {str(e)}")
        # If API is exhausted or fails completely, return safe fallback instead of 500
        fallback = {
            "summary": "AI Advisory services are temporarily busy.",
            "observations": ["Metrics are being recorded correctly.", "Analysis engine is currently rate-limited."],
            "risk_interpretation": "Unable to generate active risk interpretation at this moment.",
            "recommended_actions": ["Keep tracking your vitals.", "Try refreshing in a few minutes."],
            "escalation_notice": None
        }
        return jsonify(fallback), 200
