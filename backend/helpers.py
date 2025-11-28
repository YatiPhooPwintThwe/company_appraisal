import re
import requests
from typing import List, Optional, Tuple, Dict
from flask import current_app
from sqlalchemy import func
from models import User, Notification, Post, Reply

MAX_CONTENT_LENGTH = 2000
ALLOWED_EMOJI_LENGTH = 10

# ---------------------------------------
# PERSPECTIVE API MODERATION
# ---------------------------------------
def check_banned_content(PERSPECTIVE_API_KEY: str, text: str) -> bool:
    """
    Returns True if the content is toxic.
    Uses Google Perspective API.
    """
    if not PERSPECTIVE_API_KEY:
        current_app.logger.warning("⚠️ No Perspective API key configured.")
        return False  # allow content if no moderation

    url = "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"
    payload = {
        "comment": {"text": text},
        "languages": ["en"],
        "requestedAttributes": {
            "TOXICITY": {},
            "INSULT": {},
            "PROFANITY": {},
            "THREAT": {}
        }
    }

    try:
        response = requests.post(url, json=payload, params={"key": PERSPECTIVE_API_KEY}, timeout=5)
        response.raise_for_status()
        result = response.json()

        current_app.logger.debug(f"Perspective API result: {result}")

        scores = {
            attr: result["attributeScores"][attr]["summaryScore"]["value"]
            for attr in result.get("attributeScores", {})
        }

        # Flag if any score ≥ 0.8
        flagged = (
        scores.get("INSULT", 0) >= 0.7 or
        scores.get("TOXICITY", 0) >= 0.65 or
        scores.get("PROFANITY", 0) >= 0.6 or
        scores.get("THREAT", 0) >= 0.3
        )

        return flagged

    except requests.RequestException as e:
        current_app.logger.error(f"Perspective API request failed: {e}")
        return False  # fail open
    except Exception as e:
        current_app.logger.exception("Unexpected error in Perspective API moderation")
        return False  # fail open

# ---------------------------------------
# MENTION HANDLING
# ---------------------------------------
MENTION_REGEX = r'@([A-Za-z0-9][A-Za-z0-9\s\.\'\-@]+?)(?=\s|$|[.,!?;:])'

def extract_mentions(text: Optional[str]) -> List[str]:
    if not text:
        return []
    raw = re.findall(MENTION_REGEX, text)
    return [m.strip().rstrip(".,!?;:") for m in raw if m and m.strip()]

def resolve_mention(token: str) -> Tuple[Optional[User], Optional[Dict]]:
    """
    Resolve a mention token to a User.
    Returns (User or None, error dict or None)
    """
    user = User.query.filter(func.lower(User.email) == token.lower()).first()
    if user:
        return user, None

    user = User.query.filter(func.lower(User.login_id) == token.lower()).first()
    if user:
        return user, None

    exact = User.query.filter(func.lower(User.name) == token.lower()).all()
    if len(exact) == 1:
        return exact[0], None
    if len(exact) > 1:
        return None, {"error": f"Multiple users named '{token}'", "options": [u.to_json() for u in exact]}

    partial = User.query.filter(User.name.ilike(f"%{token}%")).all()
    if len(partial) == 1:
        return partial[0], None
    if len(partial) > 1:
        return None, {"error": f"Multiple matching users for '{token}'", "options": [u.to_json() for u in partial]}

    return None, {"error": f"No user found for '{token}'"}

def notify_tagged_users(db, item, mentions: List[str]):
    for raw in set(mentions or []):
        user, err = resolve_mention(raw)
        if err:
            current_app.logger.info(f"Mention resolution error: {err}")
            continue
        notif = Notification(
            user_id=user.id,
            message=f"You were tagged in a {'post' if isinstance(item, Post) else 'reply'}",
            post_id=item.id if isinstance(item, Post) else getattr(item, 'post_id', None),
            reply_id=item.id if isinstance(item, Reply) else None,
            poll_id=None
        )
        db.session.add(notif)

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to commit notifications: {e}")
        db.session.rollback()


