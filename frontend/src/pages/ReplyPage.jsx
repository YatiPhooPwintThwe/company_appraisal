import React, { useEffect, useState, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "../utils/axiosInstance.js";
import toast from "react-hot-toast";
import { FaImage, FaSmile } from "react-icons/fa";
import { SiGiphy } from "react-icons/si";
import { AiOutlineEdit, AiOutlineDelete } from "react-icons/ai";
import EmojiPicker from "emoji-picker-react";
import { GiphyFetch } from "@giphy/js-fetch-api";
import { Grid } from "@giphy/react-components";

const GIPHY_API_KEY = import.meta.env.VITE_GIPHY_API_KEY;

const ReplyPage = () => {
  const { id: postId } = useParams();
  const navigate = useNavigate();
  const token = localStorage.getItem("token");
  const authHeaders = { Authorization: `Bearer ${token}` };

  const [post, setPost] = useState(null);
  const [replies, setReplies] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);

  // Create states
  const [content, setContent] = useState("");
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [gifUrl, setGifUrl] = useState("");
  const [deleteImage, setDeleteImage] = useState(false);
  const [deleteGif, setDeleteGif] = useState(false);

  // UI toggles
  const [emojiTarget, setEmojiTarget] = useState("content");
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [showGifPicker, setShowGifPicker] = useState(false);
  // gifPickerFor: null => create mode; replyId => edit mode for that reply
  const [gifPickerFor, setGifPickerFor] = useState(null);
  const [gifQuery, setGifQuery] = useState("");

  // Edit states
  const [editingReplyId, setEditingReplyId] = useState(null);
  const [editingContent, setEditingContent] = useState("");
  const [editingImageFile, setEditingImageFile] = useState(null);
  const [editingImagePreview, setEditingImagePreview] = useState(null);
  const [editingGifUrl, setEditingGifUrl] = useState("");
  const [editingDeleteImage, setEditingDeleteImage] = useState(false);
  const [editingDeleteGif, setEditingDeleteGif] = useState(false);

  const gifAPI = useMemo(() => new GiphyFetch(GIPHY_API_KEY), []);

  // Helpers
  const timeAgo = (dateString) => {
    if (!dateString) return "";
    const now = new Date();
    const past = new Date(dateString);
    const diffSec = Math.floor((now - past) / 1000);
    if (diffSec < 60) return diffSec <= 1 ? "1 sec ago" : `${diffSec} secs ago`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60)
      return diffMin === 1 ? "1 min ago" : `${diffMin} mins ago`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24)
      return diffHour === 1 ? "1 hour ago" : `${diffHour} hours ago`;
    const diffDay = Math.floor(diffHour / 24);
    if (diffDay < 7) return diffDay === 1 ? "1 day ago" : `${diffDay} days ago`;
    const diffWeek = Math.floor(diffDay / 7);
    if (diffWeek < 4)
      return diffWeek === 1 ? "1 week ago" : `${diffWeek} weeks ago`;
    const diffMonth = Math.floor(diffDay / 30);
    if (diffMonth < 12)
      return diffMonth === 1 ? "1 month ago" : `${diffMonth} months ago`;
    const diffYear = Math.floor(diffDay / 365);
    return diffYear === 1 ? "1 year ago" : `${diffYear} years ago`;
  };

  const insertAtCursor = (text, target = "content") => {
    const textarea = document.getElementById(`${target}-textarea`);
    if (!textarea) {
      target === "content"
        ? setContent((c) => c + text)
        : setEditingContent((c) => c + text);
      return;
    }
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const before =
      target === "content"
        ? content.substring(0, start)
        : editingContent.substring(0, start);
    const after =
      target === "content"
        ? content.substring(end)
        : editingContent.substring(end);
    const newText = before + text + after;
    if (target === "content") setContent(newText);
    else setEditingContent(newText);
    setTimeout(() => {
      textarea.selectionStart = textarea.selectionEnd = start + text.length;
      textarea.focus();
    }, 0);
  };

  const handleEmojiClick = (emojiData) => {
    insertAtCursor(emojiData.emoji, emojiTarget);
  };

  // Data fetch
  useEffect(() => {
    const fetchCurrentUser = async () => {
      try {
        const res = await api.get("/users/me", {
          headers: authHeaders,
        });
        setCurrentUser(res.data);
      } catch (err) {
        console.error(err);
      }
    };
    fetchCurrentUser();
  }, []);

  useEffect(() => {
    const fetchPostAndReplies = async () => {
      try {
        const [postRes, repliesRes] = await Promise.all([
          api.get(`/posts/${postId}`, { headers: authHeaders }),
          api.get(`/posts/${postId}/replies`, { headers: authHeaders }),
        ]);
        setPost(postRes.data);
        setReplies(repliesRes.data.replies || []);
      } catch (err) {
        console.error(err);
        toast.error("Failed to load post");
      }
    };
    fetchPostAndReplies();
  }, [postId]);

  // Upload image helper (cloudinary / upload endpoint)
  const handleImageUpload = async (file, isEditing = false) => {
    if (!file) return;
    if (!isEditing) setGifUrl("");
    else setEditingGifUrl("");
    try {
      const formData = new FormData();
      formData.append("image", file);
      const res = await api.post("/upload", formData, {
        headers: authHeaders,
      });
      // res.data.url expected
      if (!isEditing) {
        setImagePreview(res.data.url);
        setImageFile(file);
        setDeleteImage(false);
      } else {
        setEditingImagePreview(res.data.url);
        setEditingImageFile(file);
        setEditingDeleteImage(false);
      }
    } catch (err) {
      console.error(err);
      toast.error("Image upload failed");
    }
  };

  // GIF select: distinguish create vs edit using gifPickerFor
  const handleGifSelect = (gif) => {
    const url = gif?.images?.original?.url || gif?.images?.fixed_height?.url;
    if (gifPickerFor === null) {
      // create mode
      setGifUrl(url);
      setImagePreview(null);
      setImageFile(null);
      setDeleteImage(false);
      setDeleteGif(false);
    } else {
      // edit mode for reply id = gifPickerFor
      setEditingGifUrl(url);
      setEditingImagePreview(null);
      setEditingImageFile(null);
      setEditingDeleteImage(false);
      setEditingDeleteGif(false);
    }
    setShowGifPicker(false);
    setGifPickerFor(null);
  };

  // Create reply
  const createReply = async () => {
    if (!content && !imagePreview && !gifUrl)
      return toast.error("Reply cannot be empty");
    try {
      const fd = new FormData();
      fd.append("post_id", postId);
      fd.append("content", content || "");
      if (imagePreview) fd.append("image_url", imagePreview);
      if (imageFile) fd.append("image", imageFile);
      if (deleteImage) fd.append("delete_image", "true");
      if (gifUrl) fd.append("gif", gifUrl); // send as 'gif' (backend expects 'gif' for form)
      if (deleteGif) fd.append("delete_gif", "true");

      const res = await api.post("/replies", fd, {
        headers: authHeaders,
      });
      // server now returns reply JSON including user
      setReplies((prev) => [...prev, res.data]);

      // reset create form
      setContent("");
      setImagePreview(null);
      setImageFile(null);
      setGifUrl("");
      setDeleteImage(false);
      setDeleteGif(false);
      setShowGifPicker(false);
      toast.success("Reply added!");
    } catch (err) {
      console.error(err);
      toast.error(err.response?.data?.error || "Failed to reply");
    }
  };

  // Start editing
  const startEditingReply = (reply) => {
    setEditingReplyId(reply.id);
    setEditingContent(reply.content || "");
    setEditingImagePreview(reply.imageUrl || null);
    setEditingGifUrl(reply.gifUrl || "");
    setEditingImageFile(null);
    setEditingDeleteImage(false);
    setEditingDeleteGif(false);
  };

  // Update reply
  const updateReply = async (replyId) => {
    if (!editingContent && !editingImagePreview && !editingGifUrl)
      return toast.error("Reply cannot be empty");
    try {
      const fd = new FormData();
      fd.append("content", editingContent || "");

      if (editingImageFile) fd.append("image", editingImageFile);
      else if (editingDeleteImage) fd.append("delete_image", "true");

      // IMPORTANT: send 'gif' form field (string URL) so backend picks gif_from_form
      if (editingGifUrl) fd.append("gif", editingGifUrl);
      else if (editingDeleteGif) fd.append("delete_gif", "true");

      const res = await api.put(`/replies/${replyId}`, fd, {
        headers: authHeaders,
      });
      setReplies((prev) => prev.map((r) => (r.id === replyId ? res.data : r)));

      // reset edit states
      setEditingReplyId(null);
      setEditingContent("");
      setEditingImagePreview(null);
      setEditingImageFile(null);
      setEditingGifUrl("");
      setEditingDeleteImage(false);
      setEditingDeleteGif(false);
      toast.success("Reply updated!");
    } catch (err) {
      console.error(err);
      toast.error(err.response?.data?.error || "Failed to update reply");
    }
  };

  const deleteReply = async (replyId) => {
    if (!confirm("Delete reply?")) return;
    try {
      await api.delete(`/replies/${replyId}`, { headers: authHeaders });
      setReplies((prev) => prev.filter((r) => r.id !== replyId));
      toast.success("Reply deleted");
    } catch (err) {
      console.error(err);
      toast.error("Delete failed");
    }
  };

  const toggleLike = async (replyId) => {
    try {
      const res = await api.post(
        `/replies/${replyId}/like`,
        {},
        { headers: authHeaders }
      );
      setReplies((prev) =>
        prev.map((r) =>
          r.id === replyId ? { ...r, likeCount: res.data.likeCount } : r
        )
      );
    } catch (err) {
      console.error(err);
    }
  };

  const fetchGifs = (offset) => {
    const limit = 9;
    return gifQuery.trim().length > 0
      ? gifAPI.search(gifQuery, { offset, limit })
      : gifAPI.trending({ offset, limit });
  };

  // open gif picker in create or edit mode
  const openGifPicker = (forReplyId = null) => {
    setGifPickerFor(forReplyId); // null => create; replyId => edit
    setShowGifPicker(true);
    setShowEmojiPicker(false);
  };

  return (
    <div className="p-4 max-w-3xl mx-auto">
      {/* Post */}
      {post && (
        <div className="bg-white p-4 rounded-lg shadow mb-4">
          <div className="flex gap-3 items-center mb-2">
            <img
              src={post.user?.avatarUrl || "/default-avatar.png"}
              className="w-10 h-10 rounded-full border"
            />
            <div>
              <div className="font-semibold">
                {post.user?.name || "Unknown"}
              </div>
              <div className="text-xs text-gray-500">
                {timeAgo(post.createdAt)}
              </div>
            </div>
          </div>
          <p className="whitespace-pre-line">{post.content}</p>
          {post.image_url && (
            <img src={post.image_url} className="mt-2 rounded-lg max-h-80" />
          )}
          {post.gif_url && (
            <img src={post.gif_url} className="mt-2 rounded-lg max-h-80" />
          )}
        </div>
      )}

      {/* Reply input */}
      <div className="bg-white p-4 rounded-lg shadow mb-4">
        <textarea
          id="content-textarea"
          className="w-full border p-2 rounded resize-none"
          rows={4}
          placeholder="Write a reply..."
          value={content}
          onChange={(e) => setContent(e.target.value)}
        />

        {/* Previews */}
        <div
          className={`${imagePreview || gifUrl ? "mb-6" : ""} space-y-3 mt-2`}
        >
          {imagePreview && (
            <div className="relative w-full max-h-40 border rounded overflow-hidden">
              <img
                src={imagePreview}
                className="w-full h-full object-contain"
              />
              <button
                onClick={() => {
                  setImagePreview(null);
                  setImageFile(null);
                  setDeleteImage(true);
                }}
                className="absolute top-2 right-2 bg-white rounded-full p-1 text-red-500 shadow hover:bg-red-100"
              >
                <AiOutlineDelete size={20} />
              </button>
            </div>
          )}
          {gifUrl && (
            <div className="relative w-full max-h-40 border rounded overflow-hidden">
              <img src={gifUrl} className="w-full h-full object-contain" />
              <button
                onClick={() => {
                  setGifUrl("");
                  setDeleteGif(true);
                }}
                className="absolute top-2 right-2 bg-white rounded-full p-1 text-red-500 shadow hover:bg-red-100"
              >
                <AiOutlineDelete size={20} />
              </button>
            </div>
          )}
        </div>

        {/* Action icons */}
        <div className="flex items-center space-x-4 text-xl mt-2">
          <label className="cursor-pointer text-gray-500 hover:text-gray-700">
            <FaImage size={20} />
            <input
              type="file"
              accept="image/*"
              hidden
              onChange={(e) => handleImageUpload(e.target.files[0])}
            />
          </label>

          <div className="relative">
            <button
              type="button"
              onClick={() => openGifPicker(null)}
              className="text-gray-500 hover:text-gray-700"
            >
              <SiGiphy size={20} />
            </button>
            {showGifPicker && gifPickerFor === null && (
              <div className="absolute z-50 bg-white border p-3 rounded shadow-lg w-[420px] mt-2">
                <div className="max-h-60 overflow-auto">
                  <Grid
                    width={400}
                    columns={3}
                    gutter={6}
                    fetchGifs={fetchGifs}
                    noLink
                    onGifClick={(gif, e) => {
                      e.preventDefault();
                      handleGifSelect(gif);
                    }}
                  />
                </div>
                <button
                  onClick={() => setShowGifPicker(false)}
                  className="mt-2 px-3 py-1 text-sm border rounded"
                >
                  Close
                </button>
              </div>
            )}
          </div>

          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setEmojiTarget("content");
                setShowEmojiPicker((v) => !v);
                setShowGifPicker(false);
              }}
              className="text-gray-500 hover:text-gray-700"
            >
              <FaSmile size={20} />
            </button>
            {showEmojiPicker && (
              <div className="absolute z-50 mt-2">
                <EmojiPicker
                  onEmojiClick={(emoji) => handleEmojiClick(emoji)}
                />
              </div>
            )}
          </div>
        </div>

        <button
          onClick={createReply}
          className="w-full mt-3 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Reply
        </button>
      </div>

      {/* Replies */}
      <div className="space-y-3">
        {replies.map((reply) => (
          <div
            key={reply.id}
            className="bg-white p-3 rounded-lg shadow relative"
          >
            {/* Header */}
            <div className="flex justify-between items-start mb-2">
              <div className="flex items-center gap-3">
                <img
                  src={reply.user?.avatarUrl || "/default-avatar.png"}
                  className="w-8 h-8 rounded-full border"
                />
                <div>
                  <div className="font-semibold text-sm">
                    {reply.user?.name || "Unknown"}
                  </div>
                  <div className="text-xs text-gray-500">
                    {timeAgo(reply.createdAt)}
                  </div>
                </div>
              </div>

              {/* Edit & Delete */}
              {currentUser?.id === reply.user?.id &&
                editingReplyId !== reply.id && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => startEditingReply(reply)}
                      className="text-blue-500 hover:text-blue-700"
                    >
                      <AiOutlineEdit size={18} />
                    </button>
                    <button
                      onClick={() => deleteReply(reply.id)}
                      className="text-red-500 hover:text-red-700"
                    >
                      <AiOutlineDelete size={18} />
                    </button>
                  </div>
                )}
            </div>

            {/* Content / Editing */}
            {editingReplyId === reply.id ? (
              <>
                <textarea
                  id="editing-textarea"
                  className="w-full border p-2 rounded mb-2"
                  value={editingContent}
                  onChange={(e) => setEditingContent(e.target.value)}
                />

                {editingImagePreview && (
                  <div className="relative w-full max-h-40 border rounded overflow-hidden mb-2">
                    <img
                      src={editingImagePreview}
                      className="w-full h-full object-contain"
                    />
                    <button
                      onClick={() => {
                        setEditingImagePreview(null);
                        setEditingImageFile(null);
                        setEditingDeleteImage(true);
                      }}
                      className="absolute top-2 right-2 bg-white rounded-full p-1 text-red-500 shadow hover:bg-red-100"
                    >
                      <AiOutlineDelete size={20} />
                    </button>
                  </div>
                )}

                {editingGifUrl && (
                  <div className="relative w-full max-h-40 border rounded overflow-hidden mb-2">
                    <img
                      src={editingGifUrl}
                      className="w-full h-full object-contain"
                    />
                    <button
                      onClick={() => {
                        setEditingGifUrl("");
                        setEditingDeleteGif(true);
                      }}
                      className="absolute top-2 right-2 bg-white rounded-full p-1 text-red-500 shadow hover:bg-red-100"
                    >
                      <AiOutlineDelete size={20} />
                    </button>
                  </div>
                )}

                <div className="flex items-center space-x-4 text-xl mt-2">
                  <label className="cursor-pointer text-gray-500 hover:text-gray-700">
                    <FaImage size={20} />
                    <input
                      type="file"
                      accept="image/*"
                      hidden
                      onChange={(e) =>
                        handleImageUpload(e.target.files[0], true)
                      }
                    />
                  </label>
                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => {
                        setEmojiTarget("editing");
                        setShowEmojiPicker((v) => !v);
                        setShowGifPicker(false);
                      }}
                      className="text-gray-500 hover:text-gray-700"
                    >
                      <FaSmile size={20} />
                    </button>
                    {showEmojiPicker && emojiTarget === "editing" && (
                      <div className="absolute z-50 mt-2">
                        <EmojiPicker onEmojiClick={handleEmojiClick} />
                        <button
                          className="mt-1 px-2 py-1 text-sm border rounded"
                          onClick={() => setShowEmojiPicker(false)}
                        >
                          Close
                        </button>
                      </div>
                    )}
                  </div>

                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => openGifPicker(reply.id)}
                      className="text-gray-500 hover:text-gray-700"
                    >
                      <SiGiphy size={20} />
                    </button>
                    {showGifPicker && gifPickerFor === reply.id && (
                      <div className="absolute z-50 bg-white border p-3 rounded shadow-lg w-[420px] mt-2">
                        <input
                          type="text"
                          placeholder="Search GIFs"
                          value={gifQuery}
                          onChange={(e) => setGifQuery(e.target.value)}
                          className="w-full p-2 border rounded mb-2 text-sm"
                        />
                        <div className="max-h-60 overflow-auto">
                          <Grid
                            width={400}
                            columns={3}
                            gutter={6}
                            fetchGifs={fetchGifs}
                            noLink
                            onGifClick={(gif, e) => {
                              e.preventDefault();
                              handleGifSelect(gif);
                            }}
                          />
                        </div>
                        <button
                          onClick={() => {
                            setShowGifPicker(false);
                            setGifPickerFor(null);
                          }}
                          className="mt-2 px-3 py-1 text-sm border rounded"
                        >
                          Close
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex gap-2 mt-2">
                  <button
                    onClick={() => updateReply(reply.id)}
                    className="bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setEditingReplyId(null)}
                    className="bg-gray-400 text-white px-3 py-1 rounded hover:bg-gray-500"
                  >
                    Cancel
                  </button>
                </div>
              </>
            ) : (
              <>
                <p className="whitespace-pre-line">{reply.content}</p>
                {reply.imageUrl && (
                  <img
                    src={reply.imageUrl}
                    className="mt-1 rounded-lg max-h-80"
                  />
                )}
                {reply.gifUrl && (
                  <img
                    src={reply.gifUrl}
                    className="mt-1 rounded-lg max-h-80"
                  />
                )}

                <div className="flex items-center gap-3 mt-2 text-gray-500 text-sm">
                  <button onClick={() => toggleLike(reply.id)}>
                    👍 {reply.likeCount || 0}
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
      </div>

      <button
        type="button"
        onClick={() => navigate(-1)}
        className="fixed bottom-6 left-6 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 shadow-lg"
      >
        Back
      </button>
    </div>
  );
};

export default ReplyPage;
