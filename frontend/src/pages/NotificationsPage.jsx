import React, { useEffect, useState } from "react";
import api from "../utils/axiosInstance.js";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";

const NotificationPage = () => {
  const [notifications, setNotifications] = useState([]);
  const navigate = useNavigate();

  // -----------------------
  // Fetch notifications
  // -----------------------
  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const res = await api.get("/api/notifications", {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        });

        // Normalize data: ensure actor object and consistent date key
        const normalized = Array.isArray(res.data)
          ? res.data.map((n) => ({
              ...n,
              actor: n.actor || {
                name: "System",
                avatarUrl: "/default-avatar.png",
              },
              createdAt:
                n.created_at || n.createdAt || n.created_at_iso || null,
            }))
          : [];
        setNotifications(normalized);
      } catch (err) {
        console.error(err);
        toast.error("Failed to load notifications");
        setNotifications([]);
      }
    };

    fetchNotifications();
  }, []);

  // -----------------------
  // Mark notification as read
  // -----------------------
  const markAsRead = async (notifId) => {
    try {
      await api.post(
        `/api/notifications/${notifId}/read`,
        {},
        {
          headers: { Authorization: `Bearer ${localStorage.getItem("token")}` },
        }
      );
      setNotifications((prev) =>
        prev.map((n) => (n.id === notifId ? { ...n, is_read: true } : n))
      );
    } catch (err) {
      console.error(err);
      toast.error("Failed to mark notification as read");
    }
  };

  // -----------------------
  // Render action text
  // -----------------------
  const renderActionText = (notif) => {
    switch (notif.action_type) {
      case "tagged":
        return "tagged you in a post";
      case "new_post":
        return "posted a new post";
      case "new_poll":
        return "created a new poll";
      case "system":
        return "did something";
      default:
        return notif.message || "";
    }
  };

  // -----------------------
  // Handle click
  // -----------------------
  const handleClick = async (notif) => {
    await markAsRead(notif.id);
    if (notif.post_id) navigate(`/posts/${notif.post_id}`);
    else if (notif.poll_id) navigate(`/polls/${notif.poll_id}`);
  };
  // -----------------------
  // Format time to SGT (Asia/Singapore) showing only hour:minute AM/PM
  // -----------------------
  const formatSGTTime = (isoString) => {
    if (!isoString) return "";
    const hasTZ = /(?:Z|[+-]\d{2}:\d{2})$/.test(isoString);
    const normalized = hasTZ ? isoString : `${isoString}Z`;

    try {
      const date = new Date(normalized);
      // defensive: if invalid date, return empty
      if (isNaN(date.getTime())) return "";

      // Use Intl.DateTimeFormat for consistent timezone conversion
      const fmt = new Intl.DateTimeFormat("en-US", {
        timeZone: "Asia/Singapore",
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
      });
      return fmt.format(date); // e.g. "2:13 PM"
    } catch (e) {
      console.error("formatSGTTime error", e, isoString);
      return "";
    }
  };

  // -----------------------
  // Render
  // -----------------------
  return (
    <div className="min-h-screen bg-gray-50 p-4 flex flex-col items-center">
      {/* HEADER */}
      <header className="w-full max-w-6xl flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">Notifications ✨</h1>
      </header>

      {/* NOTIFICATION LIST */}
      <div className="w-full max-w-6xl bg-white p-6 rounded-xl shadow border">
        {notifications.length === 0 ? (
          <p className="text-center text-gray-500 py-10">
            No notifications yet.
          </p>
        ) : (
          <ul>
            {notifications.map((n) => (
              <li
                key={n.id}
                className={`flex items-center p-3 mb-2 rounded-md cursor-pointer ${
                  n.is_read
                    ? "bg-gray-100"
                    : n.action_type === "system"
                    ? "bg-yellow-100"
                    : "bg-blue-100"
                }`}
                onClick={() => handleClick(n)}
              >
                <img
                  src={n.actor.avatarUrl || "/default-avatar.png"}
                  alt={n.actor.name || "System"}
                  className="w-10 h-10 rounded-full mr-3"
                />
                <div>
                  <span className="font-semibold">
                    {n.actor.name || "System"}
                  </span>{" "}
                  {renderActionText(n)}
                  <div className="text-xs text-gray-500">
                    {formatSGTTime(n.createdAt)}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* BACK BUTTON */}
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

export default NotificationPage;
