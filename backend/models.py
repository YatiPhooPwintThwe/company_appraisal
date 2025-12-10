from extensions import db, bcrypt
from flask import request
from datetime import timezone, datetime
from flask_jwt_extended import get_jwt_identity


def format_datetime(dt: datetime):
    if not dt:
        return None
    return dt.strftime("%m/%d/%Y, %I:%M %p")


# -------------------- USER --------------------
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    login_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="employee")
    avatar_url = db.Column(db.String(255))
    email = db.Column(db.String(150), unique=True, nullable=True)
    position = db.Column(db.String(100))
    department = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    posts = db.relationship("Post", backref="author", lazy="select", cascade="all, delete-orphan")
    replies = db.relationship("Reply", backref="author", lazy="select", cascade="all, delete-orphan")
    votes = db.relationship("Vote", back_populates="user", lazy="select")
    notifications = db.relationship("Notification", backref="user", lazy="select", cascade="all, delete-orphan", foreign_keys="Notification.user_id")
    notifications_as_actor = db.relationship("Notification", lazy="select", foreign_keys="Notification.actor_id")
    polls_created = db.relationship("Poll", backref="created_by_user", lazy="select", cascade="all, delete-orphan")
    likes = db.relationship("Like", backref="user", lazy="select", cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)

    def role_lower(self):
        return (self.role or "").lower()

    def to_json(self):
        avatar_full_url = None
        if self.avatar_url:
            url = str(self.avatar_url)
            if url.startswith("http://") or url.startswith("https://"):
                avatar_full_url = url
            else:
                url = url.lstrip("/")
                final_path = url if url.startswith("statics/") else f"statics/profile/{url}"
                try:
                    host_url = request.host_url.rstrip('/')
                except RuntimeError:
                    host_url = ""
                avatar_full_url = f"{host_url}/{final_path}" if host_url else f"/{final_path}"

        return {
            "id": self.id,
            "loginId": self.login_id,
            "name": self.name,
            "role": self.role,
            "avatarUrl": avatar_full_url,
            "email": self.email,
            "position": self.position,
            "department": self.department,
            "createdAt": self.created_at.replace(tzinfo=timezone.utc).isoformat(),
            "updatedAt": self.updated_at.replace(tzinfo=timezone.utc).isoformat(),
        }


# -------------------- POST --------------------
class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    gif_url = db.Column(db.String(255), nullable=True)
    pinned = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    edited_at = db.Column(db.DateTime, nullable=True) 
    # relationships
    replies = db.relationship("Reply", backref="post", lazy="select", cascade="all, delete-orphan")
    likes = db.relationship("Like", backref="post", lazy="select", cascade="all, delete-orphan")
    
    def edit(self, user: "User", new_content: str):
        if self.author_id != user.id:
            raise PermissionError("Only post author can edit this post.")
        self.content = new_content

    def delete(self, user: "User"):
        if self.author_id != user.id and user.role_lower() != "admin":
            raise PermissionError("You do not have permission to delete this post.")
        db.session.delete(self)

    def to_json(self):
        return {
            "id": self.id,
            "authorId": self.author_id,
            "content": self.content,
            "imageUrl": self.image_url,
            "gifUrl": self.gif_url,
            "pinned": self.pinned,
            "likeCount": len(self.likes),
            "createdAt": self.created_at.replace(tzinfo=timezone.utc).isoformat(),

        }


# -------------------- REPLY --------------------
class Reply(db.Model):
    __tablename__ = "replies"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    gif_url = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    edited_at = db.Column(db.DateTime, nullable=True)

    likes = db.relationship("Like", backref="reply", lazy="select", cascade="all, delete-orphan")
    
    def edit(self, user: "User", new_content: str):
        if self.author_id != user.id:
            raise PermissionError("Only reply author can edit this reply.")
        self.content = new_content

    def delete(self, user: "User"):
        if self.author_id != user.id and user.role_lower() != "admin":
            raise PermissionError("You do not have permission to delete this reply.")
        db.session.delete(self)

    def to_json(self, logged_in_user_id=None):
        return {
            "id": self.id,
            "postId": self.post_id,
            "authorId": self.author_id,
            "content": self.content,
            "imageUrl": self.image_url,
            "gifUrl": self.gif_url,
            "likeCount": len(self.likes),
            "userLiked": any(l.user_id == logged_in_user_id for l in self.likes) if logged_in_user_id else False,
            "createdAt": self.created_at.replace(tzinfo=timezone.utc).isoformat(),
            "user": self.author.to_json() if self.author else {
                "id": None, "name": "Unknown", "avatarUrl": "/default-avatar.png"

            }
        }
        
# -------------------- LIKE --------------------
class Like(db.Model):
    __tablename__ = "likes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=True)
    reply_id = db.Column(db.Integer, db.ForeignKey("replies.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "post_id", name="unique_user_post_like"),
        db.UniqueConstraint("user_id", "reply_id", name="unique_user_reply_like"),
    )

    def to_json(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "postId": self.post_id,
            "replyId": self.reply_id,
            "createdAt": self.created_at.replace(tzinfo=timezone.utc).isoformat(),

        }


# -------------------- POLL --------------------
class Poll(db.Model):
    __tablename__ = "polls"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    end_at = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    options = db.relationship("PollOption", backref="poll", lazy="select", cascade="all, delete-orphan")

    def has_expired(self) -> bool:
        return datetime.utcnow() > self.end_at

    def _current_user_vote(self, user_id: int = None):
        if user_id is None:

            try:
                user_jwt = get_jwt_identity()
                if not user_jwt:
                    return None
                user_id = int(user_jwt)
            except RuntimeError:
                return None
        return (

            Vote.query.join(PollOption, Vote.poll_option_id == PollOption.id)
            .filter(Vote.user_id == user_id, PollOption.poll_id == self.id)
            .first()
        )

    def to_json(self, include_votes=False, user_id=None):
        user_vote = self._current_user_vote(user_id)
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "createdBy": self.created_by_id,
            "createdAt": self.created_at.replace(tzinfo=timezone.utc).isoformat(),
            "endAt": self.end_at.replace(tzinfo=timezone.utc).isoformat(),
            "isActive": self.is_active,
            "hasExpired": self.has_expired(),
            "hasVoted": bool(user_vote),
            "userVoteOptionId": user_vote.poll_option_id if user_vote else None,
            "options": [o.to_json(include_votes) for o in self.options],
        }


class PollOption(db.Model):
    __tablename__ = "poll_options"

    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id"), nullable=False)
    text = db.Column(db.String(200), nullable=False)

    votes = db.relationship(
        "Vote",
        back_populates="option",
        lazy="select",
        cascade="all, delete-orphan"
    )
    def to_json(self, include_votes=False):
        data = {"id": self.id, "pollId": self.poll_id, "text": self.text}
        if include_votes:
            data["voteCount"] = len(self.votes)
            data["voters"] = [
                {
                    "id": v.user.id,
                    "name": v.user.name,
                    "avatarUrl": (getattr(v.user, "avatar_url", None) or "/default-avatar.png")
                
                }
                for v in self.votes
            ]
        return data


class Vote(db.Model):
    __tablename__ = "votes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    poll_option_id = db.Column(db.Integer, db.ForeignKey("poll_options.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint("user_id", "poll_option_id", name="one_vote_per_option"),
    )

    # Relationships
    # Only define one backref to avoid mapper conflict
    # User.votes already defines backref="votes", so no need here
    option = db.relationship("PollOption",back_populates="votes")
    user = db.relationship("User", back_populates="votes")
    def to_json(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "pollOptionId": self.poll_option_id,
            "createdAt": self.created_at.replace(tzinfo=timezone.utc).isoformat(),

        }


# -------------------- NOTIFICATION --------------------
class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # the one who triggered
    action_type = db.Column(db.String(50))
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=True)
    reply_id = db.Column(db.Integer, db.ForeignKey("replies.id"), nullable=True)
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id"), nullable=True)
    actor = db.relationship("User", foreign_keys=[actor_id], lazy="joined")

    
    def to_json(self):
        actor_data = None
        if self.actor:
            actor_data = {
                "id": self.actor.id,
                "name": self.actor.name,
                "avatarUrl": self.actor.avatar_url or "/default-avatar.png"
            }

        return {
            "id": self.id,
            "userId": self.user_id,
            "message": self.message,
            "createdAt": self.created_at.replace(tzinfo=timezone.utc).isoformat(),
            "isRead": self.is_read,
            "postId": self.post_id,
            "replyId": self.reply_id,
            "pollId": self.poll_id,
            "actor": actor_data
        }