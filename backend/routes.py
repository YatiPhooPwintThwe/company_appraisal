# routes.py
from sqlalchemy import func
from datetime import datetime
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from models import User, Post, Reply, Poll, PollOption, Vote, Like, Notification
from helpers import (
    check_banned_content,
    extract_mentions,
    notify_tagged_users,
    create_notification,
    notify_all_non_admins
)

import cloudinary.uploader

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
    @app.route('/api/login', methods=['POST'])
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

    @app.route("/users/me", methods=["GET"])
    @jwt_required()
    def get_current_user():
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        return jsonify(user.to_json()), 200

    # -----------------------
    # Posts
    # -----------------------
    @app.route("/upload", methods=["POST"])
    @jwt_required()
    def upload_image():

        file = request.files.get("image")
        if not file:

            return jsonify({"error": "No file provided"}), 400

        try:
            result = cloudinary.uploader.upload(file)
            return jsonify({"url": result["secure_url"]})
        except Exception as e:
            return jsonify({"error": str(e)}), 500


    @app.route("/posts", methods=["GET"])
    @jwt_required()
    def get_posts():
        logged_in_user_id = int(get_jwt_identity())
        posts = Post.query.order_by(Post.pinned.desc(), Post.created_at.desc()).all()
        results = []
        for p in posts:
            reply_count = db.session.query(func.count(Reply.id)).filter(Reply.post_id == p.id).scalar()
            results.append({
                **p.to_json(),
                "user": p.author.to_json() if p.author else None,
                "likeCount": Like.query.filter_by(post_id=p.id).count(),
                "userLiked": Like.query.filter_by(post_id=p.id, user_id=logged_in_user_id).first() is not None,
                "replyCount": reply_count,
                "image_url": p.image_url,
                "gif_url": p.gif_url,
            })
        return jsonify(results), 200

    @app.route("/posts/<int:post_id>", methods=["GET"])
    @jwt_required()
    def get_post(post_id):
        logged_in_user_id = int(get_jwt_identity())
        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404
        reply_count = db.session.query(func.count(Reply.id)).filter(Reply.post_id == post.id).scalar()
        return jsonify({
            **post.to_json(),
            "user": post.author.to_json() if post.author else None,
            "likeCount": Like.query.filter_by(post_id=post.id).count(),
            "userLiked": Like.query.filter_by(post_id=post.id, user_id=logged_in_user_id).first() is not None,
            "replyCount": reply_count,
            "image_url": post.image_url,
            "gif_url": post.gif_url,

        }), 200

    @app.route("/posts", methods=["POST"])
    @jwt_required()
    def create_post():
        logged_in_user_id = int(get_jwt_identity())
        user = User.query.get(logged_in_user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        content = request.form.get("content", "").strip()
        image_file = request.files.get("image")
        gif_file = request.files.get("gif")
        pinned = bool(request.form.get("pinned", False)) if user.role_lower() == "admin" else False
        image_url = None
        gif_url = None
        

        # Cloudinary uploads
        if image_file:
            try:
                upload_result = cloudinary.uploader.upload(image_file)
                image_url = upload_result.get("secure_url")
                image_public_id = upload_result.get("public_id")
            except Exception:
                return jsonify({"error": "Failed to upload image"}), 500

        if gif_file:
            try:
                upload_result = cloudinary.uploader.upload(gif_file)
                gif_url = upload_result.get("secure_url")
                gif_public_id = upload_result.get("public_id")
            except Exception:
                return jsonify({"error": "Failed to upload gif"}), 500

        if not content and not image_url and not gif_url:
            return jsonify({"error": "Content, image, or gif required"}), 400
        if content and len(content) > MAX_CONTENT_LENGTH:
            return jsonify({"error": f"Content too long (max {MAX_CONTENT_LENGTH})"}), 400

        if content:
            try:
                if check_banned_content(PERSPECTIVE_API_KEY, content):
                    return jsonify({"error": "Your content contains unsafe or toxic language."}), 403
            except Exception:
                current_app.logger.exception("Moderation check failed")
                return jsonify({"error": "Unable to validate content safety"}), 503

       

        post = Post(
            author_id=user.id,
            content=content,
            image_url=image_url,
            gif_url=gif_url,
            pinned=pinned,
            edited_at=None
        )
        db.session.add(post)
        commit_or_rollback()

        mentions = extract_mentions(content) if content else []
        if mentions:
            try:
                notify_tagged_users(db, post, mentions)
            except Exception:
                current_app.logger.exception("Failed to notify tagged users")

        # Optional: notify all users if admin
        if user.role_lower() == "admin":
            try:
                notify_all_non_admins(db, actor_id=user.id, action_type="new_post", post=post)
            except Exception:
                current_app.logger.exception("Failed to notify all users about admin post")

        return jsonify(post.to_json()), 201

    @app.route("/posts/<int:post_id>", methods=["PUT"])
    @jwt_required()
    def edit_post(post_id):
        logged_in_user_id = int(get_jwt_identity())
        user = User.query.get(logged_in_user_id)
        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404
        if int(post.author_id) != logged_in_user_id:

            return jsonify({"error": "Only the post author can edit this post"}), 403

        new_content = (request.form.get("content") or "").strip()
        image_file = request.files.get("image")
        gif_from_form = request.form.get("gif", None)       # string url or "" or None
        delete_image_flag = (request.form.get("delete_image") or "").lower() in ("1", "true", "yes")
        delete_gif_flag = (request.form.get("delete_gif") or "").lower() in ("1", "true", "yes")

        # start from existing values
        image_url = post.image_url
        gif_url = post.gif_url

        # If a new image file is uploaded -> upload and set image_url, clear gif_url
        if image_file:
            try:
                upload_result = cloudinary.uploader.upload(image_file, folder="posts")
                image_url = upload_result.get("secure_url")
                gif_url = None
            except Exception:
                return jsonify({"error": "Failed to upload image"}), 500
        else:
            # if frontend signalled delete_image -> clear image
            if delete_image_flag:
                image_url = None

        # GIF handling: if a gif URL is provided, set it (and clear image); if explicit delete -> clear gif
        if gif_from_form is not None:
            gif_from_form = gif_from_form.strip()
            if gif_from_form:
                gif_url = gif_from_form
                image_url = None  # prefer gif if user selected one
            else:
                # empty string sent -> explicit delete
                gif_url = None
        elif delete_gif_flag:
            gif_url = None

        # ensure at least one of content/image/gif present
        if not new_content and not image_url and not gif_url:
            return jsonify({"error": "Content, image, or gif required"}), 400

        if new_content and len(new_content) > MAX_CONTENT_LENGTH:
            return jsonify({"error": f"Content too long (max {MAX_CONTENT_LENGTH})"}), 400

        if new_content:
            try:
                if check_banned_content(PERSPECTIVE_API_KEY, new_content):
                    return jsonify({"error": "Your content contains unsafe or toxic language."}), 403
            except Exception:
                current_app.logger.exception("Moderation check failed")
                return jsonify({"error": "Unable to validate content safety"}), 503

        post.content = new_content or post.content
        post.image_url = image_url
        post.gif_url = gif_url
        post.edited_at = datetime.utcnow()
        commit_or_rollback()

        # include image/gif in response so frontend can refresh
        response = { **post.to_json(), "image_url": post.image_url, "gif_url": post.gif_url }
        return jsonify(response), 200


    @app.route("/posts/<int:post_id>", methods=["DELETE"])
    @jwt_required()
    def delete_post(post_id):
        logged_in_user_id = int(get_jwt_identity())
        user = User.query.get(logged_in_user_id)
        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404
        if post.author_id != logged_in_user_id and (user.role_lower() != "admin"):
            return jsonify({"error": "Only the post author or admin can delete this post"}), 403

        db.session.delete(post)
        commit_or_rollback()
        return jsonify({"message": "Post deleted"}), 200

    @app.route("/posts/<int:post_id>/like", methods=["POST"])
    @jwt_required()
    def toggle_post_like(post_id):
        logged_in_user_id = int(get_jwt_identity())
        user = User.query.get(logged_in_user_id)
        post = Post.query.get(post_id)
        if not user or not post:
            return jsonify({"error": "Post or user not found"}), 404

        existing_like = Like.query.filter_by(user_id=user.id, post_id=post.id).first()
        if existing_like:
            db.session.delete(existing_like)
            message = "Like removed"
        else:
            like = Like(user_id=user.id, post_id=post.id)
            db.session.add(like)
            message = "Post liked"
        commit_or_rollback()

        like_count = Like.query.filter_by(post_id=post.id).count()
        return jsonify({"message": message, "likeCount": like_count}), 200


    @app.route("/posts/<int:post_id>/toggle-pin", methods=["POST"])
    @jwt_required()
    def toggle_pin(post_id):
        logged_in_user_id = int(get_jwt_identity())
        user = User.query.get(logged_in_user_id)
        if not user or user.role_lower() != "admin":
            return jsonify({"error": "Only admin can pin/unpin posts"}), 403
        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404
        post.pinned = not post.pinned
        db.session.commit()

        return jsonify({"success": True, "pinned": post.pinned}), 200

    # -----------------------
    # Replies
    # -----------------------
    @app.route("/posts/<int:post_id>/replies", methods=["GET"])
    @jwt_required()
    def get_post_replies(post_id):
        logged_in_user_id = int(get_jwt_identity())
        post = Post.query.get(post_id)
        if not post:
            return jsonify({"error": "Post not found"}), 404

        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
        replies = Reply.query.filter_by(post_id=post.id).order_by(Reply.created_at.asc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        results = [r.to_json(logged_in_user_id) for r in replies.items]
        return jsonify({
           "postId": post.id,
           "totalReplies": replies.total,
           "page": page,
           "perPage": per_page,
           "replies": results
        }), 200

        
    @app.route("/replies", methods=["POST"])
    @jwt_required()
    def create_reply():
        logged_in_user_id = int(get_jwt_identity())
        user = User.query.get(logged_in_user_id)
        post_id = request.form.get("post_id")
        post = Post.query.get(post_id)
        if not user or not post:
            return jsonify({"error": "User or Post not found"}), 404

        content = (request.form.get("content") or "").strip()
        image_file = request.files.get("image")
        gif_file = request.files.get("gif")
        delete_image_flag = (request.form.get("delete_image") or "").lower() in ("1","true","yes")
        delete_gif_flag = (request.form.get("delete_gif") or "").lower() in ("1","true","yes")
        gif_from_form = request.form.get("gif", None)  # string URL
        image_url = None
        gif_url = None

        # Cloudinary uploads
        if image_file:
            try:
                upload_result = cloudinary.uploader.upload(image_file)
                image_url = upload_result.get("secure_url")
            except Exception:
                return jsonify({"error": "Failed to upload image"}), 500

         # Handle GIF
        if gif_file:
            try:
                upload_result = cloudinary.uploader.upload(gif_file)
                gif_url = upload_result.get("secure_url")
            except Exception:
                return jsonify({"error": "Failed to upload gif"}), 500
        elif gif_from_form:
            gif_url = gif_from_form

        # Apply explicit deletes
        if delete_image_flag:
            image_url = None
        if delete_gif_flag:
            gif_url = None

        if not content and not image_url and not gif_url:
            return jsonify({"error": "Content, image, or gif required"}), 400
        if content and len(content) > MAX_CONTENT_LENGTH:
            return jsonify({"error": f"Content too long (max {MAX_CONTENT_LENGTH})"}), 400

        if content:
            try:
               if check_banned_content(PERSPECTIVE_API_KEY, content):
                    return jsonify({"error": "Your content contains unsafe or toxic language."}), 403
            except Exception:
               current_app.logger.exception("Moderation check failed")
               return jsonify({"error": "Unable to validate content safety"}), 503

        reply = Reply(
            post_id=post.id,
            author_id=user.id,
            content=content,
            image_url=image_url,
            gif_url=gif_url,
            edited_at=None
        )
        db.session.add(reply)
        commit_or_rollback()
         # Ensure author info is attached for frontend
        reply_json = reply.to_json()
        reply_json["user"] = {
            "id": user.id,
            "name": user.name,
            "avatarUrl": user.avatar_url or "/default-avatar.png"
        }

        

        return jsonify(reply.to_json()), 201
        return jsonify(reply_json), 201

    @app.route("/replies/<int:reply_id>", methods=["PUT"])
    @jwt_required()
    def edit_reply(reply_id):
        logged_in_user_id = int(get_jwt_identity())
        user = User.query.get(logged_in_user_id)
        reply = Reply.query.get(reply_id)
        if not reply:
            return jsonify({"error": "Reply not found"}), 404
        if reply.author_id != logged_in_user_id:
            return jsonify({"error": "Only the reply author can edit this reply"}), 403

        new_content = (request.form.get("content") or "").strip()
        image_file = request.files.get("image")
        gif_file = request.files.get("gif")
        gif_from_form = request.form.get("gif", None)
        delete_image_flag = (request.form.get("delete_image") or "").lower() in ("1","true","yes")
        delete_gif_flag = (request.form.get("delete_gif") or "").lower() in ("1","true","yes")
        image_url = reply.image_url
        gif_url = reply.gif_url

        # Upload files if present
        if image_file:
            try:
               upload_result = cloudinary.uploader.upload(image_file)
               image_url = upload_result.get("secure_url")
               gif_url = None  # prefer image
            except Exception:
               return jsonify({"error": "Failed to upload image"}), 500
        elif delete_image_flag:
            image_url = None

        if gif_file:
            try:
               upload_result = cloudinary.uploader.upload(gif_file)
               gif_url = upload_result.get("secure_url")
               image_url = None
            except Exception:
               return jsonify({"error": "Failed to upload gif"}), 500
        elif gif_from_form is not None:
            gif_from_form = gif_from_form.strip()
            if gif_from_form:
                gif_url = gif_from_form
                image_url = None
            else:
                gif_url = None
        elif delete_gif_flag:
            gif_url = None

        if not new_content and image_url is None and gif_url is None:
            return jsonify({"error": "Content, image, or gif required"}), 400

        if new_content and len(new_content) > MAX_CONTENT_LENGTH:
            return jsonify({"error": f"Content too long (max {MAX_CONTENT_LENGTH})"}), 400

        if new_content:
            try:
                
                if check_banned_content(PERSPECTIVE_API_KEY, new_content):
                    return jsonify({"error": "Your content contains unsafe or toxic language."}), 403
            except Exception:
                current_app.logger.exception("Moderation check failed")
                return jsonify({"error": "Unable to validate content safety"}), 503

        reply.content = new_content or reply.content
        reply.image_url = image_url 
        reply.gif_url = gif_url 
        reply.edited_at = datetime.utcnow()
        commit_or_rollback()
       
        return jsonify(reply.to_json()), 200

    @app.route("/replies/<int:reply_id>", methods=["DELETE"])
    @jwt_required()
    def delete_reply(reply_id):
        logged_in_user_id = int(get_jwt_identity())
        user = User.query.get(logged_in_user_id)
        reply = Reply.query.get(reply_id)

        if not reply:
            return jsonify({"error": "Reply not found"}), 404

        if reply.author_id != logged_in_user_id and (user.role_lower() != "admin"):
            return jsonify({"error": "Only the reply author or admin can delete this reply"}), 403

        db.session.delete(reply)
        commit_or_rollback()
        return jsonify({"message": "Reply deleted"}), 200

    @app.route("/replies/<int:reply_id>/like", methods=["POST"])
    @jwt_required()
    def toggle_reply_like(reply_id):
        logged_in_user_id = int(get_jwt_identity())
        user = User.query.get(logged_in_user_id)
        reply = Reply.query.get(reply_id)
        if not user or not reply:
            return jsonify({"error": "Reply or user not found"}), 404

        existing_like = Like.query.filter_by(user_id=user.id, reply_id=reply.id).first()
        if existing_like:
            db.session.delete(existing_like)
            message = "Like removed"
        else:
            like = Like(user_id=user.id, reply_id=reply.id)
            db.session.add(like)
            message = "Reply liked"
        commit_or_rollback()

        like_count = Like.query.filter_by(reply_id=reply.id).count()
        return jsonify({"message": message, "likeCount": like_count}), 200

    # -----------------------
    # Polls
    # -----------------------
    @app.route("/polls", methods=["GET"])
    @jwt_required()
    def get_all_polls():
        polls = Poll.query.order_by(Poll.created_at.desc()).all()
        polls_data = [p.to_json(include_votes=True) for p in polls]
        return jsonify(polls_data), 200

    @app.route("/polls/active", methods=["GET"])
    @jwt_required()
    def get_active_poll():
        poll = Poll.query.filter_by(is_active=True).order_by(Poll.created_at.desc()).first()
        if not poll:
            return jsonify(None), 200
        user_id = get_jwt_identity()
        poll_data = poll.to_json(include_votes=True)
       
        return jsonify(poll_data), 200

    @app.route("/polls", methods=["POST"])
    @jwt_required()
    def create_poll():
        logged_in_user_id = int(get_jwt_identity())
        user = User.query.get(logged_in_user_id)
        if not user or user.role_lower() != "admin":
            return jsonify({"error": "Only admins can create polls"}), 403

        data = request.get_json() or {}
        title = (data.get("title") or "").strip()
        description = (data.get("description") or "").strip()
        end_at_str = data.get("end_at")
        options = data.get("options") or []

        if not title or not end_at_str or not options or not isinstance(options, list) or len(options) < 2:
            return jsonify({"error": "Title, end date, and at least 2 options are required"}), 400

        try:
            end_at = datetime.fromisoformat(end_at_str)
        except Exception:
            return jsonify({"error": "Invalid end date format"}), 400

        poll = Poll(title=title, description=description, created_by_id=user.id, end_at=end_at)
       
        db.session.add(poll)
        commit_or_rollback()
        if user.role_lower() == "admin":
            try:
                notify_all_non_admins(db, actor_id=user.id, action_type="new_poll", poll=poll)
            except Exception:
                current_app.logger.exception("Failed to notify users about new poll")

        for opt_text in options:
            opt_text = opt_text.strip()
            if opt_text:
                db.session.add(PollOption(poll_id=poll.id, text=opt_text))
        commit_or_rollback()

        poll_data = poll.to_json(include_votes=True)
       

        return jsonify(poll_data), 201

    @app.route("/polls/<int:poll_id>", methods=["GET"])
    @jwt_required()
    def get_poll(poll_id):
        poll = Poll.query.get(poll_id)
        if not poll:
            return jsonify({"error": "Poll not found"}), 404
        poll_data = poll.to_json(include_votes=True)
       
        return jsonify(poll_data), 200

    @app.route("/polls/<int:poll_id>", methods=["DELETE"])
    @jwt_required()
    def delete_poll(poll_id):
        logged_in_user_id = int(get_jwt_identity())
        user = User.query.get(logged_in_user_id)
        if not user or user.role_lower() != "admin":
            return jsonify({"error": "Only admins can delete polls"}), 403

        poll = Poll.query.get(poll_id)
        if not poll:
            return jsonify({"error": "Poll not found"}), 404

        db.session.delete(poll)
        commit_or_rollback()
        return jsonify({"message": "Poll deleted"}), 200

    @app.route("/polls/<int:poll_id>/vote", methods=["POST"])
    @jwt_required()
    def vote_poll(poll_id):
        logged_in_user_id = int(get_jwt_identity())
        user = User.query.get(logged_in_user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404

        poll = Poll.query.get(poll_id)
        if not poll or poll.has_expired():
            return jsonify({"error": "Poll not found or expired"}), 404

        data = request.get_json() or {}
        option_id = data.get("option_id")
        try:
            option_id = int(option_id)
        except Exception:
             return jsonify({"error": "Invalid option id"}), 400
        
        option = PollOption.query.filter_by(id=option_id, poll_id=poll.id).first()
        if not option:
            return jsonify({"error": "Invalid option"}), 400

        existing_vote = (
        Vote.query.join(PollOption, Vote.poll_option_id == PollOption.id)
        .filter(Vote.user_id == user.id, PollOption.poll_id == poll.id)
        .first()
        )

        if existing_vote:
            existing_vote.poll_option_id = option.id
        else:
            new_vote = Vote(user_id=user.id, poll_option_id=option.id)
            db.session.add(new_vote)
        commit_or_rollback()

        poll = Poll.query.get(poll_id)
        poll_data = poll.to_json(include_votes=True)
        return jsonify(poll_data), 200
    
    @app.route("/polls/<int:poll_id>", methods=["PUT"])
    @jwt_required()
    def edit_poll(poll_id):

        logged_in_user_id = int(get_jwt_identity())
        user = User.query.get(logged_in_user_id)

        if not user or user.role_lower() != "admin":
            return jsonify({"error": "Only admins can edit polls"}), 403

        poll = Poll.query.get(poll_id)
        if not poll:
            return jsonify({"error": "Poll not found"}), 404

        data = request.get_json() or {}
        title = (data.get("title") or "").strip()
        description = (data.get("description") or "").strip()
        end_at_str = data.get("end_at")

        if not title and not description and not end_at_str:
            return jsonify({"error": "At least one field (title, description, end date) must be provided"}), 400

        if title:
            poll.title = title
        if description:
            poll.description = description
        if end_at_str:
            try:
                poll.end_at = datetime.fromisoformat(end_at_str)
            except Exception:
                return jsonify({"error": "Invalid end date format"}), 400

        commit_or_rollback()

        poll_data = poll.to_json(include_votes=True)  # keep votes intact
        return jsonify(poll_data), 200

    # -----------------------
    # Notifications
    # -----------------------
    @app.route("/notifications", methods=["GET"])
    @jwt_required()
    def get_notifications():
        logged_in_user_id = int(get_jwt_identity())
        notifs = Notification.query.filter_by(user_id=logged_in_user_id)\
            .order_by(Notification.created_at.desc()).limit(50).all()
        results = []
        for n in notifs:
            actor_name = None
            actor_avatar = None
            # Determine actor info
            if getattr(n, "actor", None):
                
                actor_name = n.actor.name
                actor_avatar = n.actor.avatar_url or "/default-avatar.png"
            else:
                # fallback: try to pick the post author or poll creator
                if n.post_id:
                    post = Post.query.get(n.post_id)
                    if post and getattr(post, "author", None):
                        actor_name = post.author.name
                        actor_avatar = post.author.avatar_url or "/default-avatar.png"
                if not actor_name and n.poll_id:
                    poll = Poll.query.get(n.poll_id)
                    # you used created_by_id on Poll; check relationship name
                    creator = getattr(poll, "created_by_user", None) if poll else None
                    if creator:
                        actor_name = creator.name
                        actor_avatar = creator.avatar_url or "/default-avatar.png"

            # final fallback
            if not actor_name:
                actor_name = "System"
                actor_avatar = "/default-avatar.png"

            results.append({
                "id": n.id,
                "actor": {
                    "name": actor_name,
                    "avatarUrl": actor_avatar
                },
                "message": n.message,
                "action_type": n.action_type,
                "post_id": n.post_id,
                "poll_id": n.poll_id,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat()
            })

        return jsonify(results), 200

    @app.route("/notifications/<int:notif_id>/read", methods=["POST"])
    @jwt_required()
    def mark_notification_read(notif_id):
        logged_in_user_id = int(get_jwt_identity())
        notif = Notification.query.get(notif_id)
        if not notif or notif.user_id != logged_in_user_id:
            return jsonify({"error": "Notification not found"}), 404
        notif.is_read = True
        commit_or_rollback()
        return jsonify({"message": "Notification marked as read"}), 200

    # DELETE ALL NOTIFICATIONS for the logged-in user
    @app.route("/notifications/clear", methods=["DELETE"])
    @jwt_required()
    def clear_notifications():
        user_id = int(get_jwt_identity())
    
        # Delete only this user's notifications
        Notification.query.filter_by(user_id=user_id).delete()

        db.session.commit()
        return jsonify({"message": "All notifications cleared"}), 200
