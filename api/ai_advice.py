from flask import Blueprint, request, jsonify, session
import os
import google.generativeai as genai
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ai_bp = Blueprint('ai', __name__)

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

    return genai.GenerativeModel(model_name="gemini-1.5-flash",
                                 safety_settings=safety_settings,
                                 system_instruction=SYSTEM_PROMPT)

@ai_bp.route('/health-advice', methods=['POST'])
def get_health_advice():
    # 1. Security Check
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    # 2. Key Check
    if not API_KEY:
        return jsonify({
            'summary': 'AI Service Unavailable',
            'observations': ['System configuration incomplete.'],
            'risk_interpretation': 'N/A',
            'recommended_actions': [],
            'escalation_notice': None
        })

    try:
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
        
        # 5. Safe Parsing
        try:
            # Strip potential markdown fences if model yields them despite instructions
            Clean_text = response.text.replace('```json', '').replace('```', '').strip()
            advice_json = json.loads(Clean_text)
            
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
            
            return jsonify(advice_json)

        except json.JSONDecodeError:
            logger.error(f"Failed to parse LLM response: {response.text}")
            return jsonify({
                "summary": "Health data analyzed.",
                "observations": ["Complex patterns detected."],
                "risk_interpretation": "Please review your vitals manually.",
                "recommended_actions": ["Consult healthcare provider if feeling unwell."],
                "escalation_notice": "Error parsing detailed advice."
            })

    except Exception as e:
        logger.error(f"AI Advisor Error: {str(e)}")
        return jsonify({'error': 'AI Service Error'}), 500
