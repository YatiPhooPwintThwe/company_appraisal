import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../utils/axiosInstance.js";
import toast from "react-hot-toast";
import { AiOutlineDelete } from "react-icons/ai";
const CreatePollPage = () => {
  const navigate = useNavigate();

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [endAt, setEndAt] = useState("");
  const [options, setOptions] = useState(["", ""]);

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  const updateOption = (index, value) => {
    const updated = [...options];
    updated[index] = value;
    setOptions(updated);
  };
  // Get current date-time in format "YYYY-MM-DDTHH:MM"
  const getMinDateTime = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    const hours = String(now.getHours()).padStart(2, "0");
    const minutes = String(now.getMinutes()).padStart(2, "0");
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  };

  const addOption = () => {
    setOptions([...options, ""]);
  };

  const removeOption = (index) => {
    if (options.length <= 2) {
      toast.error("At least 2 options are required");
      return;
    }
    setOptions(options.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    const cleanedOptions = options.map((o) => o.trim()).filter((o) => o !== "");

    if (!title.trim()) return toast.error("Title required");
    if (!endAt.trim()) return toast.error("Please select end date");
    if (cleanedOptions.length < 2)
      return toast.error("Minimum 2 poll options required");

    try {
      await api.post(
        "/polls",
        {
          title: title.trim(),
          description: description.trim(),
          end_at: endAt,
          options: cleanedOptions,
        },
        { headers }
      );

      toast.success("Poll created successfully!");
      navigate("/");
    } catch (err) {
      console.log(err);
      toast.error(err.response?.data?.error || "Failed to create poll");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6 flex justify-center">
      <div className="w-full max-w-2xl bg-white p-6 rounded-xl shadow border">
        <h1 className="text-2xl font-bold mb-4">Create New Poll 🗳️</h1>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* TITLE */}
          <div>
            <label className="block font-semibold mb-1">Poll Title</label>
            <input
              type="text"
              className="w-full p-3 border rounded-md"
              placeholder="Enter poll title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>

          {/* DESCRIPTION */}
          <div>
            <label className="block font-semibold mb-1">Description</label>
            <textarea
              className="w-full p-3 border rounded-md"
              placeholder="Write a short description..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              required
            />
          </div>

          {/* END DATE */}
          <div>
            <label className="block font-semibold mb-1">End Date</label>
            <input
              type="datetime-local"
              className="w-full p-3 border rounded-md"
              value={endAt}
              onChange={(e) => setEndAt(e.target.value)}
              required
              min={getMinDateTime()} // <-- prevents selecting past
            />
          </div>

          {/* OPTIONS */}
          <div>
            <label className="block font-semibold mb-2">Poll Options</label>

            {options.map((opt, i) => (
              <div key={i} className="flex gap-2 mb-2">
                <input
                  type="text"
                  className="flex-1 p-3 border rounded-md"
                  placeholder={`Option ${i + 1}`}
                  value={opt}
                  onChange={(e) => updateOption(i, e.target.value)}
                />
                <button
                  onClick={() => removeOption(i)}
                  className="text-red-600"
                >
                  <AiOutlineDelete size={20} />
                </button>
              </div>
            ))}

            <button
              type="button"
              onClick={addOption}
              className="mt-2 px-3 py-1 bg-blue-600 text-white rounded-md"
            >
              Add
            </button>
          </div>

          {/* SUBMIT */}
          <button
            type="submit"
            className="w-full mt-4 py-3 bg-green-600 text-white font-semibold rounded-md"
          >
            Create Poll
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
    </div>
  );
};

export default CreatePollPage;
