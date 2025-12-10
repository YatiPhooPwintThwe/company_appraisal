// ReplyItem.jsx
import React, { useState } from "react";
import { FaHeart, FaTrash, FaEdit, FaSave } from "react-icons/fa";

const ReplyItem = ({ reply, onLike, onDelete, onEdit }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(reply.content || "");

  const handleSave = () => {
    if (editContent.trim() === "") return;
    onEdit(reply.id, editContent);
    setIsEditing(false);
  };

  return (
    <div className="bg-white p-3 rounded-lg shadow">
      <div className="flex gap-3 items-center mb-2">
        <img
          src={reply.user?.avatarUrl || "/default-avatar.png"}
          alt={reply.user?.name || "Unknown"}
          className="w-9 h-9 rounded-full object-cover border border-gray-300"
        />
        <div>
          <div className="font-semibold">{reply.user?.name || "Unknown User"}</div>
          <div className="text-xs text-gray-500">
            {reply.createdAt ? new Date(reply.createdAt).toLocaleString() : ""}
          </div>
        </div>
      </div>

      {isEditing ? (
        <textarea
          className="w-full p-2 border rounded"
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
        />
      ) : (
        <p className="whitespace-pre-line">{reply.content}</p>
      )}

      {reply.imageUrl && <img src={reply.imageUrl} className="mt-2 rounded-lg max-h-60" />}
      {reply.gifUrl && <img src={reply.gifUrl} className="mt-2 rounded-lg max-h-60" />}

      <div className="flex gap-4 mt-2 text-gray-600">
        <button onClick={() => onLike(reply.id)} className="flex items-center gap-1">
          <FaHeart /> {reply.likeCount || 0}
        </button>
        <button onClick={() => onDelete(reply.id)} className="flex items-center gap-1">
          <FaTrash />
        </button>
        {isEditing ? (
          <button onClick={handleSave} className="flex items-center gap-1">
            <FaSave /> Save
          </button>
        ) : (
          <button onClick={() => setIsEditing(true)} className="flex items-center gap-1">
            <FaEdit /> Edit
          </button>
        )}
      </div>
    </div>
  );
};

export default ReplyItem;
