import React, { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import axiosInstance from "../utils/axiosInstance.js";
import toast from "react-hot-toast";
import { AiOutlineDelete } from "react-icons/ai";
import { FaImage, FaUserTag, FaSmile } from "react-icons/fa";
import { SiGiphy } from "react-icons/si";
import EmojiPicker from "emoji-picker-react";
import { GiphyFetch } from "@giphy/js-fetch-api";
import { Grid } from "@giphy/react-components";

const GIPHY_API_KEY = import.meta.env.VITE_GIPHY_API_KEY;

const CreatePostPage = () => {
  const navigate = useNavigate();

  const [user, setUser] = useState(null);
  const [content, setContent] = useState("");
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [gifUrl, setGifUrl] = useState("");
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [showGifPicker, setShowGifPicker] = useState(false);
  const [gifQuery, setGifQuery] = useState("");

  const [showUserList, setShowUserList] = useState(false);
  const [allUsers, setAllUsers] = useState([]);

  const gf = useMemo(() => new GiphyFetch(GIPHY_API_KEY), []);

  // Fetch current user
  useEffect(() => {
    const fetchUser = async () => {
      try {
        const token = localStorage.getItem("token");
        if (!token) return;
        const res = await axiosInstance.get("/api/users/me", {
          headers: { Authorization: `Bearer ${token}` },
        });
        setUser(res.data);
      } catch (err) {
        console.error("Failed to fetch current user:", err);
      }
    };
    fetchUser();
  }, []);

  // Fetch users for tagging
  useEffect(() => {
    if (!showUserList) return;
    const fetchUsers = async () => {
      try {
        const token = localStorage.getItem("token");
        const res = await axiosInstance.get("/api/users", {
          headers: { Authorization: `Bearer ${token}` },
        });
        setAllUsers(Array.isArray(res.data) ? res.data : []);
      } catch (err) {
        console.error("Failed to fetch users:", err);
      }
    };
    fetchUsers();
  }, [showUserList]);

  const handleImageChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setGifUrl(""); // remove GIF if selecting image
    setImageFile(file);
    const formData = new FormData();
    formData.append("image", file);

    try {
      const token = localStorage.getItem("token");
      const formData = new FormData();
      formData.append("image", file);

      const res = await axiosInstance.post("/api/upload", formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "multipart/form-data",
        },
      });

      setImagePreview(res.data.url); // Cloudinary URL from backend
    } catch (err) {
      console.error(err);
      toast.error("Failed to upload image");
    }
  };

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
    setShowGifPicker(false);
  };

  const insertAtCursor = (text) => {
    const textarea = document.getElementById("post-textarea");
    if (!textarea) {
      setContent((prev) => prev + text);
      return;
    }

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;

    const before = content.substring(0, start);
    const after = content.substring(end);

    const newContent = `${before}${text}${after}`;
    setContent(newContent);

    setTimeout(() => {
      const pos = start + text.length;
      textarea.selectionStart = textarea.selectionEnd = pos;
      textarea.focus();
    }, 0);
  };

  const handleEmojiClick = (emojiData) => {
    const toInsert = emojiData?.emoji || emojiData;
    insertAtCursor(toInsert);
    setShowEmojiPicker(false);
  };

  const handleUserTagClick = (username) => {
    insertAtCursor(`@${username} `);
    setShowUserList(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!content.trim() && !imagePreview && !gifUrl) {
      toast.error("Please add some content, image, or GIF");
      return;
    }

    try {
      const token = localStorage.getItem("token");
      const formData = new FormData();

      formData.append("content", content);

      // If user uploaded an image
      if (imagePreview) {
        formData.append("image", imageFile); // imageFile must store actual File
      }

      // If user selected a GIF
      if (gifUrl) {
        // You could either upload GIF to backend too, or just send URL as hidden form field
        formData.append("gif", gifUrl);
      }

      await axiosInstance.post("/api/posts", formData, {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "multipart/form-data",
        },
      });

      toast.success("Post created successfully!");
      navigate("/");
    } catch (err) {
      console.error("Create post error:", err);

      const serverMsg =
        err.response?.data?.error ||
        err.response?.data?.message ||
        "Failed to create post";
      toast.error(serverMsg);
    }
  };

  return (
    <>
      <div className="max-w-xl mx-auto mt-10 p-6 bg-white rounded shadow relative">
        <h2 className="text-xl font-bold mb-4">Create Post</h2>

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
            placeholder="What's on your mind?"
            value={content}
            onChange={(e) => setContent(e.target.value)}
          />

          <div className="flex items-center space-x-4">
            {/* Image */}
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

            {/* GIF */}
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
                  <button
                    type="button"
                    className="mt-2 px-3 py-1 text-sm border rounded"
                    onClick={() => setShowGifPicker(false)}
                  >
                    Close
                  </button>
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
                    setImagePreview(null);
                    setImageFile(null);
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
                  onClick={() => setGifUrl("")}
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
            Post
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

export default CreatePostPage;
