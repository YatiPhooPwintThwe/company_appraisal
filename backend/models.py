from datetime import datetime
from extensions import db, bcrypt

# User
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    login_id = db.Column(db.String(50), unique=True, nullable=False)  # used for @ mentions
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
    votes = db.relationship("Vote", backref="user", lazy="select", cascade="all, delete-orphan")
    notifications = db.relationship("Notification", backref="user", lazy="select", cascade="all, delete-orphan")
    polls_created = db.relationship("Poll", backref="created_by_user", lazy="select", cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password: str) -> bool:
        return bcrypt.check_password_hash(self.password_hash, password)

    def role_lower(self):
        return (self.role or "").lower()

    def to_json(self):
        return {
            "id": self.id,
            "loginId": self.login_id,
            "name": self.name,
            "role": self.role,
            "avatarUrl": self.avatar_url,
            "email": self.email,
            "position": self.position,
            "department": self.department,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

# -- Post
class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relationships
    replies = db.relationship("Reply", backref="post", lazy="select", cascade="all, delete-orphan")

    def edit(self, user: "User", new_content: str):
        """Update post content; raises PermissionError if not author."""
        if self.author_id != user.id:
            raise PermissionError("Only post author can edit this post.")
        self.content = new_content
        # DO NOT commit here

    def delete(self, user: "User"):
        """Delete post; only author or admin can delete."""
        if self.author_id != user.id and user.role_lower() != "admin":
            raise PermissionError("You do not have permission to delete this post.")
        db.session.delete(self)
        # DO NOT commit here

    def to_json(self):
        return {
            "id": self.id,
            "authorId": self.author_id,
            "content": self.content,
            "createdAt": self.created_at.isoformat(),
        }


# -- Reply
class Reply(db.Model):
    __tablename__ = "replies"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def edit(self, user: "User", new_content: str):
        """Update reply content; raises PermissionError if not author."""
        if self.author_id != user.id:
            raise PermissionError("Only reply author can edit this reply.")
        self.content = new_content
        # DO NOT commit here

    def delete(self, user: "User"):
        """Delete reply; only author or admin can delete."""
        if self.author_id != user.id and user.role_lower() != "admin":
            raise PermissionError("You do not have permission to delete this reply.")
        db.session.delete(self)
        # DO NOT commit here

    def to_json(self):
        return {
            "id": self.id,
            "postId": self.post_id,
            "authorId": self.author_id,
            "content": self.content,
            "createdAt": self.created_at.isoformat(),
        }


# -- Polls
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

    def to_json(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "createdBy": self.created_by_id,
            "createdAt": self.created_at.isoformat(),
            "endAt": self.end_at.isoformat(),
            "isActive": self.is_active,
            "hasExpired": self.has_expired(),
        }

class PollOption(db.Model):
    __tablename__ = "poll_options"

    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id"), nullable=False)
    text = db.Column(db.String(200), nullable=False)

    votes = db.relationship("Vote", backref="option", lazy="select", cascade="all, delete-orphan")

    def to_json(self):
        return {"id": self.id, "pollId": self.poll_id, "text": self.text}

class Vote(db.Model):
    __tablename__ = "votes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    poll_option_id = db.Column(db.Integer, db.ForeignKey("poll_options.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint("user_id", "poll_option_id", name="one_vote_per_option"),)

    def to_json(self):
        return {"id": self.id, "userId": self.user_id, "pollOptionId": self.poll_option_id, "createdAt": self.created_at.isoformat()}

# -- Notification
class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=True)
    reply_id = db.Column(db.Integer, db.ForeignKey("replies.id"), nullable=True)
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id"), nullable=True)

    def to_json(self):
        return {
            "id": self.id,
            "userId": self.user_id,
            "message": self.message,
            "createdAt": self.created_at.isoformat(),
            "isRead": self.is_read,
            "postId": self.post_id,
            "replyId": self.reply_id,
            "pollId": self.poll_id,
        }
