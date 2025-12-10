import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import api from "../utils/axiosInstance.js";
import toast from "react-hot-toast";

const EditPollPage = () => {
  const { pollId } = useParams();
  const navigate = useNavigate();
  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [endAt, setEndAt] = useState("");
  const [loading, setLoading] = useState(true);

  // Fetch poll data
  useEffect(() => {
    const fetchPoll = async () => {
      try {
        const res = await api.get(`/api/polls/${pollId}`, { headers });
        const poll = res.data;
        setTitle(poll.title);
        setDescription(poll.description || "");
        setEndAt(poll.endAt.slice(0, 16)); // convert ISO to "YYYY-MM-DDTHH:mm"
        setLoading(false);
      } catch (err) {
        console.error(err);
        toast.error("Failed to load poll");
        navigate("/");
      }
    };
    fetchPoll();
  }, [pollId]);

  const getMinDateTime = () => {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    const day = String(now.getDate()).padStart(2, "0");
    const hours = String(now.getHours()).padStart(2, "0");
    const minutes = String(now.getMinutes()).padStart(2, "0");
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim()) return toast.error("Title required");
    if (!endAt.trim()) return toast.error("End date required");

    try {
      await api.put(
        `/api/polls/${pollId}`,
        {
          title: title.trim(),
          description: description.trim(),
          end_at: endAt,
        },
        { headers }
      );
      toast.success("Poll updated successfully!");
      navigate("/");
    } catch (err) {
      console.log(err);
      toast.error(err.response?.data?.error || "Failed to update poll");
    }
  };

  if (loading) return <div className="p-6 text-center">Loading...</div>;

  return (
    <div className="min-h-screen bg-gray-50 p-6 flex justify-center">
      <div className="w-full max-w-2xl bg-white p-6 rounded-xl shadow border">
        <h1 className="text-2xl font-bold mb-4">Edit Poll 📝</h1>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* TITLE */}
          <div>
            <label className="block font-semibold mb-1">Poll Title</label>
            <input
              type="text"
              className="w-full p-3 border rounded-md"
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
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
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
              min={getMinDateTime()}
              required
            />
          </div>

          <div className="mt-16">
            <button
              type="submit"
              className="w-full mt-8 py-3 bg-blue-600 text-white font-semibold rounded-md"
            >
              Update Poll
            </button>
          </div>
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

export default EditPollPage;
