// EditPostPage.jsx
import React, { useState, useEffect, useMemo } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "../utils/axiosInstance.js";
import toast from "react-hot-toast";
import { AiOutlineDelete } from "react-icons/ai";
import { FaImage, FaUserTag, FaSmile } from "react-icons/fa";
import { SiGiphy } from "react-icons/si";
import EmojiPicker from "emoji-picker-react";
import { GiphyFetch } from "@giphy/js-fetch-api";
import { Grid } from "@giphy/react-components";

const GIPHY_API_KEY = import.meta.env.VITE_GIPHY_API_KEY;

const EditPostPage = () => {
  const navigate = useNavigate();
  const { postId } = useParams();

  const [user, setUser] = useState(null);
  const [content, setContent] = useState("");

  // media state
  const [imageFile, setImageFile] = useState(null); // file chosen locally (to send on Save)
  const [imagePreview, setImagePreview] = useState(null); // preview URL (existing URL or uploaded preview)
  const [gifUrl, setGifUrl] = useState(""); // gif url when selected

  // deletion marks (frontend only until Save)
  const [deleteImage, setDeleteImage] = useState(false);
  const [deleteGif, setDeleteGif] = useState(false);

  // UI helpers
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [showGifPicker, setShowGifPicker] = useState(false);
  const [gifQuery, setGifQuery] = useState("");
  const [showUserList, setShowUserList] = useState(false);
  const [allUsers, setAllUsers] = useState([]);

  const gf = useMemo(() => new GiphyFetch(GIPHY_API_KEY), []);

  // Fetch current user info
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) return;
        const res = await api.get("/users/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        setUser(res.data);
      } catch (err) {
        console.error(err);
      }
    };
    fetchUser();
  }, []);

  // Fetch post to edit (including image_url and gif_url)
  useEffect(() => {
    const fetchPost = async () => {
      try {
        const token = localStorage.getItem("token");
        const res = await api.get(`/posts/${postId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setContent(res.data.content || "");
        setImagePreview(res.data.image_url || null);
        setGifUrl(res.data.gif_url || "");
        setDeleteImage(false);
        setDeleteGif(false);
      } catch (err) {
        console.error(err);
        toast.error("Failed to load post");
        navigate(-1);
      }
    };
    fetchPost();
  }, [postId, navigate]);

  // Fetch all users for tagging (only when opened)
  useEffect(() => {
    if (!showUserList) return;
    const fetchUsers = async () => {
      try {
        const token = localStorage.getItem("token");
        const res = await api.get("/users", {
          headers: { Authorization: `Bearer ${token}` },
        });
        setAllUsers(Array.isArray(res.data) ? res.data : []);
      } catch (err) {
        console.error(err);
      }
    };
    fetchUsers();
  }, [showUserList]);

  const fetchGifs = (offset) => {
    const limit = 9;
    if (gifQuery.trim().length > 0)
      return gf.search(gifQuery, { offset, limit });
    return gf.trending({ offset, limit });
  };

  const handleGifSelect = (gif) => {
    const url =
      gif?.images?.fixed_height?.url ||
      gif?.images?.downsized?.url ||
      gif?.images?.original?.url;
    setGifUrl(url);
    setImagePreview(null);
    setImageFile(null);
    setDeleteImage(false); // since user chose gif, image won't be kept
    setDeleteGif(false);
    setShowGifPicker(false);
  };

  // When user chooses a local image file:
  // - upload to /api/upload to get a preview URL (optional but fast UX)
  // - save file in imageFile to actually submit to backend on Save
  const handleImageChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setGifUrl("");
    setDeleteGif(false);
    setImageFile(file);
    setDeleteImage(false);

    try {
      const token = localStorage.getItem("token");
      // upload preview (you already have /api/upload)
      const formData = new FormData();
      formData.append("image", file);
      const upload = await api.post("/upload", formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "multipart/form-data",
        },
      });
      // show preview from upload response
      setImagePreview(upload.data.url || null);
    } catch (err) {
      console.error(err);
      toast.error("Failed to upload preview");
    }
  };

  // Insert text at cursor in textarea
  const insertAtCursor = (text) => {
    const textarea = document.getElementById("post-textarea");
    if (!textarea) {
      setContent((c) => c + text);
      return;
    }
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const before = content.substring(0, start);
    const after = content.substring(end);
    const newContent = before + text + after;
    setContent(newContent);
    setTimeout(() => {
      textarea.selectionStart = textarea.selectionEnd = start + text.length;
      textarea.focus();
    }, 0);
  };

  const handleEmojiClick = (emoji) => {
    insertAtCursor(emoji.emoji);
    setShowEmojiPicker(false);
  };

  const handleUserTagClick = (username) => {
    insertAtCursor(`@${username} `);
    setShowUserList(false);
  };

  // Save / Submit edited post
  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem("token");
      const fd = new FormData();
      fd.append("content", content || "");

      // Image: if new file chosen -> include file.
      // If user deleted existing image and no new file -> send delete_image flag.
      if (imageFile) {
        fd.append("image", imageFile);
      } else if (deleteImage) {
        fd.append("delete_image", "true");
      }

      // GIF: send gif URL (if non-empty) — backend will set gif_url and clear image_url.
      // If user explicitly deleted gif -> send delete_gif flag.
      if (gifUrl) {
        fd.append("gif", gifUrl);
      } else if (deleteGif) {
        fd.append("delete_gif", "true");
      } else {
        // If neither gif nor deleteGif nor imageFile, do nothing (backend will keep existing unless delete flag present)
        // optionally append empty gif to explicitly clear, but we use delete_gif flag instead
      }

      await api.put(`/posts/${postId}`, fd, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "multipart/form-data",
        },
      });
      toast.success("Post updated!");
      navigate(-1);
    } catch (err) {
      console.error(err);
      toast.error(
        err.response?.data?.error ||
          err.response?.data?.message ||
          "Failed to update post"
      );
    }
  };

  return (
    <>
      <div className="max-w-xl mx-auto mt-10 p-6 bg-white rounded shadow relative">
        <h2 className="text-xl font-bold mb-4">Edit Post</h2>

        {user && (
          <div className="flex items-center gap-3 mb-4">
            <img
              src={user?.avatarUrl || "/default-avatar.png"}
              alt={user?.name || "avatar"}
              className="w-10 h-10 rounded-full object-cover border border-gray-300"
            />
            <div className="font-semibold text-gray-900">
              {user?.name || "Unknown"}
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            id="post-textarea"
            className="w-full p-2 border rounded resize-none"
            rows={4}
            placeholder="Edit your post..."
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />

          <div className="flex items-center space-x-4">
            {/* Image upload */}
            <label className="cursor-pointer text-gray-500 hover:text-gray-700">
              <FaImage size={20} />
              <input
                type="file"
                accept="image/*"
                onChange={handleImageChange}
                className="hidden"
              />
            </label>

            {/* User Tag */}
            <div className="relative">
              <button
                type="button"
                onClick={() => setShowUserList((v) => !v)}
                className="text-gray-500 hover:text-gray-700"
              >
                <FaUserTag size={20} />
              </button>
              {showUserList && (
                <div className="absolute z-50 bg-white border p-3 rounded shadow-lg w-64 mt-2 max-h-60 overflow-auto">
                  {allUsers.map((u) => (
                    <div
                      key={u.id}
                      className="flex items-center gap-2 p-1 hover:bg-gray-100 rounded cursor-pointer"
                      onClick={() => handleUserTagClick(u.name)}
                    >
                      <img
                        src={u?.avatarUrl || "/default-avatar.png"}
                        alt={u?.name || "avatar"}
                        className="w-6 h-6 rounded-full border border-gray-300"
                      />
                      <span>{u?.name || "Unknown"}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* GIF picker */}
            <div className="relative">
              <button
                type="button"
                onClick={() => {
                  setShowGifPicker((v) => !v);
                  setShowEmojiPicker(false);
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                <SiGiphy size={20} />
              </button>

              {showGifPicker && (
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
                  <div className="mt-2 flex gap-2">
                    <button
                      type="button"
                      className="px-3 py-1 text-sm border rounded"
                      onClick={() => setShowGifPicker(false)}
                    >
                      Close
                    </button>
                    <button
                      type="button"
                      className="px-3 py-1 text-sm border rounded"
                      onClick={() => {
                        // clear gif selection
                        setGifUrl("");
                        setDeleteGif(true);
                        setImagePreview(imagePreview); // no-op but keep UI consistent
                        setShowGifPicker(false);
                      }}
                    >
                      Remove GIF
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Emoji */}
            <div className="relative">
              <button
                type="button"
                onClick={() => {
                  setShowEmojiPicker((v) => !v);
                  setShowGifPicker(false);
                }}
                className="text-gray-500 hover:text-gray-700"
              >
                <FaSmile size={20} />
              </button>
              {showEmojiPicker && (
                <div className="absolute z-50 mt-2">
                  <EmojiPicker onEmojiClick={handleEmojiClick} />
                </div>
              )}
            </div>
          </div>

          {/* Previews */}
          <div className={`${imagePreview || gifUrl ? "mb-6" : ""} space-y-3`}>
            {imagePreview && (
              <div className="relative w-full border rounded overflow-hidden">
                <img
                  src={imagePreview}
                  alt="preview"
                  className="w-full h-auto object-contain"
                />
                <button
                  type="button"
                  onClick={() => {
                    // mark deletion of existing image (if it existed) or just remove chosen preview
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
              <div className="relative w-full border rounded overflow-hidden">
                <img
                  src={gifUrl}
                  alt="gif preview"
                  className="w-full h-auto object-contain"
                />
                <button
                  type="button"
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

          <button
            type="submit"
            className="w-full bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Update Post
          </button>
        </form>
      </div>

      <button
        type="button"
        onClick={() => navigate(-1)}
        className="fixed bottom-6 left-6 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 shadow-lg"
      >
        Back
      </button>
    </>
  );
};

export default EditPostPage;
