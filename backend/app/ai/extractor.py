import re
import os
import json
from groq import Groq
from app.core.constants import ALLOWED_CATEGORIES


def extract_complaint_from_transcript(transcript: str) -> dict:
    """
    Extract complaint fields from a raw transcript using AI.
    
    Uses Groq (free API) with Llama 3.1 to intelligently extract and infer fields from natural conversation.
    Never fabricates missing data. Returns None for fields that cannot be confidently inferred.
    
    Args:
        transcript: Raw transcript string from voice call
        
    Returns:
        Dictionary with extracted fields:
        {
            "flat_number": str | None,
            "category": str | None,
            "priority": str | None,
            "description": str | None
        }
    """
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        system_prompt = """You are a complaint extraction AI.

Your task: Extract structured complaint data from voice call transcripts.

STRICT RULES:
1. Extract ONLY these fields: flat_number, category, priority, description
2. If a field is NOT mentioned or cannot be confidently inferred, return null for that field
3. NEVER fabricate or guess missing information
4. Category must be one of: water, electricity, cleaning, noise, maintenance, security, other
5. Priority must be one of: low, medium, high
6. All category and priority values MUST be lowercase
7. Output valid JSON ONLY - no explanations, no markdown, no code blocks

Field Extraction Guidelines:
- flat_number: Extract apartment/unit number if mentioned (e.g., "A-101", "Flat 204", "12B")
- category: Infer from complaint keywords (leak→water, power cut→electricity, etc.)
- priority: Infer from urgency keywords (urgent→high, whenever→low, etc.)
- description: Extract the core complaint description

Output Format (strict):
{
  "flat_number": "value" or null,
  "category": "value" or null,
  "priority": "value" or null,
  "description": "value" or null
}"""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract complaint data from this transcript:\n\n{transcript}"}
            ],
            temperature=0,
            max_tokens=500
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        result = json.loads(result_text)
        
        # Normalize and validate
        if result.get("category"):
            result["category"] = result["category"].lower()
            if result["category"] not in ALLOWED_CATEGORIES:
                result["category"] = None
        
        if result.get("priority"):
            result["priority"] = result["priority"].lower()
            if result["priority"] not in ["low", "medium", "high"]:
                result["priority"] = None
        
        # Ensure all expected fields exist
        return {
            "flat_number": result.get("flat_number"),
            "category": result.get("category"),
            "priority": result.get("priority"),
            "description": result.get("description")
        }
        
    except Exception as e:
        # On any error, return all None fields
        print(f"AI extraction error: {e}")
        return {
            "flat_number": None,
            "category": None,
            "priority": None,
            "description": None
        }


def extract_fields(text: str) -> dict:
    """
    Extract complaint fields from raw user text.
    
    This is a rule-based, deterministic parser that attempts to identify:
    - flat_number (via regex)
    - category (via keyword matching)
    - priority (via keyword matching)
    - description (always the full text)
    
    Args:
        text: Raw user input
        
    Returns:
        Dictionary with extracted fields. Only confidently detected fields are filled.
        {
            "flat_number": str | None,
            "category": str | None,
            "priority": str | None,
            "description": str
        }
    """
    text_lower = text.lower()
    
    return {
        "flat_number": _extract_flat_number(text),
        "category": _extract_category(text_lower),
        "priority": _extract_priority(text_lower),
        "description": text.strip()
    }


def _extract_flat_number(text: str) -> str | None:
    """
    Extract flat/unit number using regex patterns.
    
    Supports formats:
    - A-101, B-204
    - A 101, B 204
    - Flat 302, Unit 12B
    - 302, 12B (standalone numbers)
    
    Returns first match found, or None if no match.
    """
    patterns = [
        r'\b([A-Z]-?\s?\d{1,4}[A-Z]?)\b',
        r'\b(flat|unit)\s+([A-Z0-9-]+)\b',
        r'\b(\d{1,4}[A-Z])\b',
        r'\b([A-Z]\s?\d{1,4})\b',
        r'^\s*(\d{2,4})\s*$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            if 'flat' in pattern or 'unit' in pattern:
                return match.group(2).strip()
            else:
                return match.group(1).strip()
    
    return None


def _extract_category(text_lower: str) -> str | None:
    """
    Extract category using keyword matching.
    
    Maps keywords to canonical category values from ALLOWED_CATEGORIES.
    Returns None if no confident match is found.
    """
    category_keywords = {
        "water": ["water", "leak", "leaking", "pipe", "plumbing", "tap", "sink", "flush", "tank", "drainage"],
        "electricity": ["electricity", "electric", "power", "light", "current", "bulb", "switch", "wiring", "socket", "fan", "outage"],
        "cleaning": ["clean", "cleaning", "garbage", "trash", "dirt", "dirty", "sweep", "dustbin", "waste", "litter"],
        "noise": ["noise", "noisy", "loud", "sound", "music", "disturbance", "shouting", "party"],
        "maintenance": ["repair", "broken", "fix", "maintenance", "damage", "damaged", "crack", "paint", "door", "window", "wall"],
        "security": ["security", "guard", "theft", "lock", "locked", "gate", "key", "safe", "safety", "intruder"]
    }
    
    matched_categories = {}
    
    for category, keywords in category_keywords.items():
        if category not in ALLOWED_CATEGORIES:
            continue
            
        match_count = sum(1 for keyword in keywords if keyword in text_lower)
        if match_count > 0:
            matched_categories[category] = match_count
    
    if matched_categories:
        return max(matched_categories, key=matched_categories.get)
    
    return None


def _extract_priority(text_lower: str) -> str | None:
    """
    Extract priority using keyword matching.
    
    Maps keywords to priority levels: low, medium, high.
    If multiple signals exist, chooses the highest priority.
    Returns None if no signal is detected.
    """
    priority_keywords = {
        "high": ["urgent", "urgently", "emergency", "immediately", "asap", "critical", "serious", "severe", "high"],
        "medium": ["soon", "important", "needed", "quickly", "necessary", "medium"],
        "low": ["whenever", "not urgent", "can wait", "no hurry", "eventually", "low"]
    }
    
    detected_priorities = []
    
    for priority, keywords in priority_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                detected_priorities.append(priority)
                break
    
    if not detected_priorities:
        return None
    
    priority_order = {"high": 3, "medium": 2, "low": 1}
    return max(detected_priorities, key=lambda p: priority_order[p])

