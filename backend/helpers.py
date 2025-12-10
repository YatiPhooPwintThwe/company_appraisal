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

        flagged = (
            scores.get("INSULT", 0) >= 0.35 or
            scores.get("TOXICITY", 0) >= 0.40 or
            scores.get("PROFANITY", 0) >= 0.50 or
            scores.get("THREAT", 0) >= 0.20
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
    # Try email first
    user = User.query.filter(func.lower(User.email) == token.lower()).first()
    if user:
        return user, None

    # Try login_id
    user = User.query.filter(func.lower(User.login_id) == token.lower()).first()
    if user:
        return user, None

    # Exact name match
    exact_matches = User.query.filter(func.lower(User.name) == token.lower()).all()
    if len(exact_matches) == 1:
        return exact_matches[0], None
    if len(exact_matches) > 1:
        return None, {"error": f"Multiple users named '{token}'", "options": [u.to_json() for u in exact_matches]}

    # Partial name match
    partial_matches = User.query.filter(User.name.ilike(f"%{token}%")).all()
    if len(partial_matches) == 1:
        return partial_matches[0], None
    if len(partial_matches) > 1:
        return None, {"error": f"Multiple matching users for '{token}'", "options": [u.to_json() for u in partial_matches]}

    return None, {"error": f"No user found for '{token}'"}

# helpers.py (replace relevant functions)

def create_notification(db, user_id, actor_id, action_type, post_id=None, poll_id=None, reply_id=None, message=None):
    """
    Create a Notification record. If message is not provided, generate one from action_type.
    """
    if not message:
        if action_type == "tagged":
            message = "You were tagged in a post"
        elif action_type == "new_post":
            message = "An admin created a new post" if actor_id else "A new post was created"
        elif action_type == "new_poll":
            message = "A new poll was created"
        else:
            message = "You have a new notification"

    notif = Notification(
        user_id=user_id,
        actor_id=actor_id,
        action_type=action_type,
        message=message,
        post_id=post_id,
        poll_id=poll_id,
        reply_id=reply_id
    )
    db.session.add(notif)
    # don't commit here — caller can batch commit; but callers in this project usually commit after calling
    return notif


def notify_tagged_users(db, item, mentions: List[str]):
    """
    Create 'tagged' notifications for each resolved user.
    `item` should be a Post or Reply instance (or similar) with author_id and id/post_id.
    """
    actor_id = getattr(item, "author_id", None)
    if not actor_id:
        current_app.logger.warning("Tagged notification skipped: no actor_id found")
        return

    for raw_mention in set(mentions or []):
        user, err = resolve_mention(raw_mention)
        if err or not user:
            current_app.logger.debug(f"Skipping mention '{raw_mention}': {err}")
            continue

        # create notification with actor_id and derived message
        create_notification(
            db=db,
            user_id=user.id,
            actor_id=actor_id,
            action_type="tagged",
            post_id=getattr(item, "id", None) if isinstance(item, Post) else getattr(item, "post_id", None),
            message=None
        )

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to commit tagged notifications: {e}")
        db.session.rollback()


def notify_all_non_admins(db, actor_id, action_type, post=None, poll=None):
    """
    Notify all non-admin users (except actor) about admin action.
    """
    users = User.query.filter(User.role != "admin").all()

    for u in users:
        if u.id == actor_id:
            continue

        create_notification(
            db=db,
            user_id=u.id,
            actor_id=actor_id,
            action_type=action_type,
            post_id=getattr(post, "id", None),
            poll_id=getattr(poll, "id", None),
            message=None
        )

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(f"Failed to commit notifications: {e}")
        db.session.rollback()
