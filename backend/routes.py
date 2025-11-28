from sqlalchemy import func
from datetime import datetime
from typing import Optional
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from models import User, Post, Reply, Poll, PollOption, Vote, Notification
from helpers import check_banned_content, extract_mentions, notify_tagged_users, resolve_mention

MAX_CONTENT_LENGTH = 2000

def register_routes(app, db, PERSPECTIVE_API_KEY):
    if db is None:
        raise RuntimeError("register_routes requires a SQLAlchemy 'db' parameter")

    def commit_or_rollback():
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

    # -----------------------
    # Authentication
    # -----------------------
    @app.route('/login', methods=['POST'])
    def login():
        data = request.get_json() or {}
        login_id = data.get("login_id")
        password = data.get("password")
        if not login_id or not password:
            return jsonify({"error": "login_id and password are required"}), 400

        user = User.query.filter_by(login_id=login_id).first()
        if not user or not user.check_password(password):
            return jsonify({"error": "Invalid credentials"}), 401

        access_token = create_access_token(identity=str(user.id))
        return jsonify({"message": "Login successful", "token": access_token, "user": user.to_json()}), 200

    # -----------------------
    # Users
    # -----------------------
    @app.route('/users', methods=['GET'])
    @jwt_required()
    def list_users():
        users = User.query.order_by(User.name.asc()).all()
        return jsonify([u.to_json() for u in users]), 200

    @app.route('/users/<int:user_id>', methods=['GET'])
    @jwt_required()
    def get_user(user_id):
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify(user.to_json()), 200

    @app.route('/users/search', methods=['GET'])
    @jwt_required()
    def search_users():
        q = (request.args.get('q') or "").strip()
        if not q:
            return jsonify([]), 200

        q_lower = q.lower()
        matches = User.query.filter(
            (func.lower(User.login_id).like(f"{q_lower}%")) |
            (func.lower(User.name).like(f"%{q_lower}%"))
        ).order_by(User.name).limit(25).all()

        results = [
            {
                "id": u.id,
                "loginId": u.login_id,
                "name": u.name,
                "email": u.email,
                "avatarUrl": getattr(u, "avatar_url", None),
                "department": getattr(u, "department", None),
                "position": getattr(u, "position", None),
            } for u in matches
        ]
        return jsonify(results), 200

    # -----------------------
    # Posts
    # -----------------------
    @app.route("/posts", methods=["POST"])
    @jwt_required()
    def create_post():
        logged_in_user_id = get_jwt_identity()
        try:
            logged_in_user_id = int(logged_in_user_id)
        except Exception:
            return jsonify({"error": "Invalid JWT identity"}), 401

        user = User.query.get(logged_in_user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json() or {}
        content = (data.get("content") or "").strip()
        if not content:
            return jsonify({"error": "Content required"}), 400
        if len(content) > MAX_CONTENT_LENGTH:
            return jsonify({"error": f"Content too long (max {MAX_CONTENT_LENGTH} chars)"}), 400

        try:
            if check_banned_content(PERSPECTIVE_API_KEY, content):
                return jsonify({"error": "Your content contains unsafe or toxic language."}), 403
        except Exception:
            current_app.logger.exception("Moderation check failed")
            return jsonify({"error": "Unable to validate content safety"}), 503

        mentions = extract_mentions(content)
        for token in mentions:
            matched_user, err = resolve_mention(token)
            if err:
                return jsonify(err), 400

        post = Post(author_id=user.id, content=content)
        db.session.add(post)
        try:
            commit_or_rollback()
        except Exception:
            current_app.logger.exception("Failed to create post")
            return jsonify({"error": "Failed to create post (DB error)"}), 500

        if mentions:
            try:
                notify_tagged_users(db, post, mentions)
            except Exception:
                current_app.logger.exception("Failed to notify tagged users")

        return jsonify(post.to_json()), 201

    @app.route("/posts/<int:post_id>", methods=["PUT"])
    @jwt_required()
    def edit_post(post_id):
        logged_in_user_id = get_jwt_identity()
        try:
            logged_in_user_id = int(logged_in_user_id)
        except Exception:
            return jsonify({"error": "Invalid JWT identity"}), 401

        user = User.query.get(logged_in_user_id)
        post = Post.query.get(post_id)
        if not user or not post:
            return jsonify({"error": "Post or user not found"}), 404

        new_content = (request.get_json() or {}).get("content", "").strip()
        if not new_content:
            return jsonify({"error": "Content required"}), 400
        if len(new_content) > MAX_CONTENT_LENGTH:
            return jsonify({"error": f"Content too long (max {MAX_CONTENT_LENGTH})"}), 400

        try:
            if check_banned_content(PERSPECTIVE_API_KEY, new_content):
                return jsonify({"error": "Your content contains unsafe or toxic language."}), 403
        except Exception:
            current_app.logger.exception("Moderation check failed")
            return jsonify({"error": "Unable to validate content safety"}), 503

        try:
            post.edit(user, new_content)
            commit_or_rollback()
        except PermissionError as e:
            return jsonify({"error": str(e)}), 403
        except Exception:
            current_app.logger.exception("Failed to update post")
            return jsonify({"error": "Failed to update post"}), 500

        mentions = extract_mentions(new_content)
        if mentions:
            for token in mentions:
                matched_user, err = resolve_mention(token)
                if err:
                    return jsonify(err), 400
            try:
                notify_tagged_users(db, post, mentions)
            except Exception:
                current_app.logger.exception("Failed to notify tagged users on edit")

        return jsonify(post.to_json()), 200

    @app.route("/posts/<int:post_id>", methods=["DELETE"])
    @jwt_required()
    def delete_post(post_id):
        logged_in_user_id = get_jwt_identity()
        try:
            logged_in_user_id = int(logged_in_user_id)
        except Exception:
            return jsonify({"error": "Invalid JWT identity"}), 401

        user = User.query.get(logged_in_user_id)
        post = Post.query.get(post_id)
        if not user or not post:
            return jsonify({"error": "Post or user not found"}), 404

        try:
            post.delete(user)
            commit_or_rollback()
        except PermissionError as e:
            return jsonify({"error": str(e)}), 403
        except Exception:
            current_app.logger.exception("Failed to delete post")
            return jsonify({"error": "Failed to delete post"}), 500

        return jsonify({"message": "Post deleted"}), 200

    # -----------------------
    # Replies
    # -----------------------
    @app.route("/replies", methods=["POST"])
    @jwt_required()
    def create_reply():
        logged_in_user_id = get_jwt_identity()
        try:
            logged_in_user_id = int(logged_in_user_id)
        except Exception:
            return jsonify({"error": "Invalid JWT identity"}), 401

        user = User.query.get(logged_in_user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json() or {}
        post = Post.query.get(data.get("post_id"))
        if not post:
            return jsonify({"error": "Post not found"}), 404

        content = (data.get("content") or "").strip()
        if not content:
            return jsonify({"error": "Content required"}), 400
        if len(content) > MAX_CONTENT_LENGTH:
            return jsonify({"error": f"Content too long (max {MAX_CONTENT_LENGTH})"}), 400

        try:
            if check_banned_content(PERSPECTIVE_API_KEY, content):
                return jsonify({"error": "Your content contains unsafe or toxic language."}), 403
        except Exception:
            current_app.logger.exception("Moderation check failed")
            return jsonify({"error": "Unable to validate content safety"}), 503

        reply = Reply(post_id=post.id, author_id=user.id, content=content)
        db.session.add(reply)
        try:
            commit_or_rollback()
        except Exception:
            current_app.logger.exception("Failed to create reply")
            return jsonify({"error": "Failed to create reply"}), 500

        mentions = extract_mentions(content)
        if mentions:
            try:
                notify_tagged_users(db, reply, mentions)
            except Exception:
                current_app.logger.exception("Failed to notify tagged users on reply")

        return jsonify(reply.to_json()), 201

    @app.route("/replies/<int:reply_id>", methods=["PUT"])
    @jwt_required()
    def edit_reply(reply_id):
        logged_in_user_id = get_jwt_identity()
        try:
            logged_in_user_id = int(logged_in_user_id)
        except Exception:
            return jsonify({"error": "Invalid JWT identity"}), 401

        user = User.query.get(logged_in_user_id)
        reply = Reply.query.get(reply_id)
        if not user or not reply:
            return jsonify({"error": "Reply or user not found"}), 404

        content = (request.get_json() or {}).get("content", "").strip()
        if not content:
            return jsonify({"error": "Content required"}), 400
        if len(content) > MAX_CONTENT_LENGTH:
            return jsonify({"error": f"Content too long (max {MAX_CONTENT_LENGTH})"}), 400

        try:
            if check_banned_content(PERSPECTIVE_API_KEY, content):
                return jsonify({"error": "Your content contains unsafe or toxic language."}), 403
        except Exception:
            current_app.logger.exception("Moderation check failed")
            return jsonify({"error": "Unable to validate content safety"}), 503

        try:
            reply.edit(user, content)
            commit_or_rollback()
        except PermissionError as e:
            return jsonify({"error": str(e)}), 403
        except Exception:
            current_app.logger.exception("Failed to update reply")
            return jsonify({"error": "Failed to update reply"}), 500

        mentions = extract_mentions(content)
        if mentions:
            try:
                notify_tagged_users(db, reply, mentions)
            except Exception:
                current_app.logger.exception("Failed to notify tagged users on reply edit")

        return jsonify(reply.to_json()), 200

    @app.route("/replies/<int:reply_id>", methods=["DELETE"])
    @jwt_required()
    def delete_reply(reply_id):
        logged_in_user_id = get_jwt_identity()
        try:
            logged_in_user_id = int(logged_in_user_id)
        except Exception:
            return jsonify({"error": "Invalid JWT identity"}), 401

        user = User.query.get(logged_in_user_id)
        reply = Reply.query.get(reply_id)
        if not user or not reply:
            return jsonify({"error": "Reply or user not found"}), 404

        try:
            reply.delete(user)
            commit_or_rollback()
        except PermissionError as e:
            return jsonify({"error": str(e)}), 403
        except Exception:
            current_app.logger.exception("Failed to delete reply")
            return jsonify({"error": "Failed to delete reply"}), 500

        return jsonify({"message": "Reply deleted"}), 200

    # -----------------------
    # Polls
    # -----------------------
    @app.route('/polls/<int:poll_id>', methods=['GET'])
    @jwt_required()
    def get_poll_detail(poll_id):
        logged_in_user_id = get_jwt_identity()
        try:
            logged_in_user_id = int(logged_in_user_id)
        except Exception:
            logged_in_user_id = None

        poll = Poll.query.get(poll_id)
        if not poll:
            return jsonify({"error": "Poll not found"}), 404

        # Get options
        options = PollOption.query.filter_by(poll_id=poll.id).all()

        # Count votes per option
        option_votes = {}
        for opt in options:
            count = Vote.query.filter_by(poll_option_id=opt.id).count()
            option_votes[opt.id] = count

        # Check user's vote
        user_vote = None
        if logged_in_user_id:
            existing_vote = Vote.query.filter(
                Vote.user_id == logged_in_user_id,
                Vote.poll_option_id.in_([o.id for o in options])
            ).first()
            if existing_vote:
                user_vote = existing_vote.poll_option_id

        # Build response
        return jsonify({
            "id": poll.id,
            "title": poll.title,
            "description": poll.description,
            "createdBy": getattr(poll, "created_by_id", getattr(poll, "created_by", None)),
            "createdAt": poll.created_at.isoformat() if getattr(poll, "created_at", None) else None,
            "endAt": poll.end_at.isoformat() if getattr(poll, "end_at", None) else None,
            "hasExpired": poll.end_at <= datetime.utcnow(),
            "isActive": getattr(poll, "is_active", True),
            "userVotedOptionId": user_vote,
            "options": [
                {
                    "id": opt.id,
                    "text": opt.text,
                    "votes": option_votes.get(opt.id, 0),
                }
                for opt in options
            ],
            "totalVotes": sum(option_votes.values())
        }), 200

    @app.route('/polls', methods=['POST'])
    @jwt_required()
    def create_poll():
        logged_in_user_id = get_jwt_identity()
        try:
            logged_in_user_id = int(logged_in_user_id)
        except Exception:
            return jsonify({"error": "Invalid JWT identity"}), 401

        admin = User.query.get(logged_in_user_id)
        if not admin or (getattr(admin, "role", "") or "").lower() != "admin":
            return jsonify({"error": "Only admins can create polls"}), 403

        data = request.get_json() or {}
        title = data.get('title')
        end_at_raw = data.get('end_at')
        options = data.get('options', [])

        if not title or not end_at_raw:
            return jsonify({"error": "title and end_at required"}), 400

        try:
            end_dt = datetime.fromisoformat(end_at_raw)
        except Exception:
            return jsonify({"error": "end_at must be an ISO datetime string"}), 400

        poll = Poll(title=title, description=data.get('description'), created_by_id=admin.id, end_at=end_dt)
        db.session.add(poll)
        try:
            commit_or_rollback()
        except Exception:
            current_app.logger.exception("Failed to create poll")
            return jsonify({"error": "Failed to create poll"}), 500

        try:
            for opt_text in options or []:
                db.session.add(PollOption(poll_id=poll.id, text=opt_text))
            commit_or_rollback()
        except Exception:
            current_app.logger.exception("Failed to create poll options")
            return jsonify({"error": "Failed to create poll options"}), 500

        # Notify non-admin employees
        try:
            employees = User.query.filter(User.role != 'admin').all()
            for emp in employees:
                db.session.add(Notification(user_id=emp.id, message=f"New poll: {poll.title}", poll_id=poll.id))
            commit_or_rollback()
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Failed to create poll notifications")

        return jsonify(poll.to_json()), 201
    @app.route('/polls/<int:poll_id>', methods=['DELETE'])
    @jwt_required()
    def delete_poll(poll_id):
        logged_in_user_id = get_jwt_identity()
        try:
            logged_in_user_id = int(logged_in_user_id)
        except Exception:
            return jsonify({"error": "Invalid JWT identity"}), 401

        admin = User.query.get(logged_in_user_id)
        if not admin or (getattr(admin, "role", "") or "").lower() != "admin":
            return jsonify({"error": "Only admins can delete polls"}), 403

        poll = Poll.query.get(poll_id)
        if not poll:
            return jsonify({"error": "Poll not found"}), 404

        try:
            # Delete related poll options and votes first
            PollOption.query.filter_by(poll_id=poll.id).delete()
            Vote.query.filter(Vote.poll_option_id.in_([opt.id for opt in PollOption.query.filter_by(poll_id=poll.id).all()])).delete()
                # Delete notifications for this poll
            Notification.query.filter_by(poll_id=poll.id).delete()
                # Delete the poll itself
            db.session.delete(poll)
            db.session.commit()
            return jsonify({"message": "Poll deleted"}), 200
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Failed to delete poll")
            return jsonify({"error": "Failed to delete poll"}), 500


    @app.route('/polls/<int:poll_id>/vote', methods=['POST'])
    @jwt_required()
    def vote_poll(poll_id):
        logged_in_user_id = get_jwt_identity()
        try:
            logged_in_user_id = int(logged_in_user_id)
        except Exception:
            return jsonify({"error": "Invalid JWT identity"}), 401

        user = User.query.get(logged_in_user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json() or {}
        option = PollOption.query.get(data.get('poll_option_id'))
        poll = Poll.query.get(poll_id)

        if not poll or not option or option.poll_id != poll_id:
            return jsonify({"error": "Invalid poll or option"}), 404

        expired = poll.has_expired() if hasattr(poll, "has_expired") else (poll.end_at <= datetime.utcnow())
        if expired or not getattr(poll, "is_active", True):
            return jsonify({"error": "Poll expired or inactive"}), 400

        existing_vote = Vote.query.filter(
            Vote.user_id == user.id,
            Vote.poll_option_id.in_([o.id for o in PollOption.query.filter_by(poll_id=poll_id).all()])
        ).first()

        if existing_vote:
            return jsonify({"error": "Already voted"}), 400

        vote = Vote(user_id=user.id, poll_option_id=option.id)
        db.session.add(vote)
        try:
            commit_or_rollback()
            return jsonify(vote.to_json()), 201
        except Exception:
            current_app.logger.exception("Failed to cast vote")
            return jsonify({"error": "Failed to cast vote"}), 500

    # -----------------------
    # Notifications
    # -----------------------
    @app.route('/notifications', methods=['GET'])
    @jwt_required()
    def list_notifications():
        logged_in_user_id = get_jwt_identity()
        try:
            logged_in_user_id = int(logged_in_user_id)
        except Exception:
            return jsonify({"error": "Invalid JWT identity"}), 401

        user = User.query.get(logged_in_user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
        return jsonify([n.to_json() for n in notifications]), 200

    @app.route('/notifications/<int:notification_id>/read', methods=['PUT'])
    @jwt_required()
    def mark_notification_read(notification_id):
        logged_in_user_id = get_jwt_identity()
        try:
            logged_in_user_id = int(logged_in_user_id)
        except Exception:
            return jsonify({"error": "Invalid JWT identity"}), 401

        notif = Notification.query.get(notification_id)
        if not notif or notif.user_id != logged_in_user_id:
            return jsonify({"error": "Notification not found or not yours"}), 404

        notif.is_read = True
        try:
            commit_or_rollback()
            return jsonify({"message": "Notification marked as read"}), 200
        except Exception:
            current_app.logger.exception("Failed to mark notification read")
            return jsonify({"error": "Failed to mark read"}), 500
