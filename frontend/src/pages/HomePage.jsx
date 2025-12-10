import React, { useEffect, useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import toast from "react-hot-toast";
import { AiOutlineEdit, AiOutlineDelete } from "react-icons/ai";

const HomePage = () => {
  const [polls, setPolls] = useState([]);
  const [selectedPoll, setSelectedPoll] = useState(null);
  const [selectedOption, setSelectedOption] = useState(null);
  const [hasVoted, setHasVoted] = useState(false);
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentUser, setCurrentUser] = useState(null);

  const navigate = useNavigate();
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const highlightPostId = params.get("postId");
  const highlightPollId = params.get("pollId");

  const token = localStorage.getItem("token");
  const headers = { Authorization: `Bearer ${token}` };

  const timeAgo = (dateString) => {
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

  useEffect(() => {
    const fetchCurrentUser = async () => {
      try {
        const res = await axios.get("/api/users/me", { headers });
        setCurrentUser(res.data);
      } catch (err) {
        console.error(err);
      }
    };
    fetchCurrentUser();
  }, []);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const pollsRes = await axios.get("/api/polls", { headers });
        const postsRes = await axios.get("/api/posts", { headers });

        const pollsData = pollsRes.data || [];
        setPolls(pollsData);
        setSelectedPoll(pollsData[0] || null);
        setPosts(postsRes.data);
      } catch (err) {
        console.error(err);
      }
      setLoading(false);
    };
    fetchData();
  }, []);

  useEffect(() => {
    if (highlightPostId) {
      const el = document.getElementById(`post-${highlightPostId}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        el.classList.add("highlight-post");
        setTimeout(() => el.classList.remove("highlight-post"), 3000);
      }
    }

    if (highlightPollId) {
      const el = document.getElementById(`poll-${highlightPollId}`);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
        el.classList.add("highlight-post");
        setTimeout(() => el.classList.remove("highlight-post"), 3000);
      }
    }
  }, [posts]);

  const submitVote = async () => {
    if (!selectedOption || !selectedPoll) return;
    try {
      await axios.post(
        `/api/polls/${selectedPoll.id}/vote`,
        { option_id: parseInt(selectedOption, 10) },
        { headers }
      );
      const pollRes = await axios.get("/api/polls", { headers });
      setPolls(pollRes.data);
      const updatedPoll = pollRes.data.find((p) => p.id === selectedPoll.id);
      setSelectedPoll(updatedPoll);
      setHasVoted(true);
    } catch {
      alert("You already voted");
      const pollRes = await axios.get("/api/polls", { headers });
      setPolls(pollRes.data);
      const updatedPoll = pollRes.data.find((p) => p.id === selectedPoll.id);
      setSelectedPoll(updatedPoll);
    }
  };

  const toggleLike = async (postId) => {
    try {
      const res = await axios.post(
        `/api/posts/${postId}/like`,
        {},
        { headers }
      );
      setPosts((prev) =>
        prev.map((p) =>
          p.id === postId ? { ...p, likeCount: res.data.likeCount } : p
        )
      );
    } catch (err) {
      console.error(err);
    }
  };

  const handleDelete = async (postId) => {
    if (!window.confirm("Delete this post?")) return;
    try {
      await axios.delete(`/api/posts/${postId}`, { headers });
      setPosts((prev) => prev.filter((p) => p.id !== postId));
      toast.success("Post deleted");
    } catch {
      toast.error("Failed to delete");
    }
  };

  const togglePin = async (postId) => {
    try {
      await axios.post(`/api/posts/${postId}/toggle-pin`, {}, { headers });
      const postsRes = await axios.get("/api/posts", { headers });
      setPosts(postsRes.data);
    } catch {
      toast.error("Unable to pin");
    }
  };

  if (loading || !currentUser)
    return <div className="p-6 text-center">Loading...</div>;

  const isAdmin = currentUser.role === "admin";

  return (
    <div className="min-h-screen bg-gray-50 p-4 flex flex-col items-center">
      {/* HEADER */}
      <header className="w-full max-w-6xl flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold">Home Page ✨</h1>
        <nav className="flex gap-3">
          <Link
            to="/create-post"
            className="px-3 py-2 bg-yellow-500 text-black rounded-md shadow"
          >
            Create Post
          </Link>
          {isAdmin && (
            <button
              onClick={() => navigate("/create-poll")}
              className="px-3 py-2 bg-purple-600 text-white rounded-md shadow hover:bg-purple-700"
            >
              Create Poll
            </button>
          )}
          <Link
            to="/notifications"
            className="px-3 py-2 bg-blue-600 text-white rounded-md shadow"
          >
            Notifications
          </Link>
          <button
            onClick={() => {
              localStorage.removeItem("token");
              navigate("/login");
            }}
            className="px-3 py-2 bg-red-600 text-white rounded-md shadow"
          >
            Logout
          </button>
        </nav>
      </header>

      {/* MAIN GRID */}
      <div className="w-full max-w-6xl grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* POLLS LIST */}
        <div className="bg-white p-4 rounded-xl shadow border flex flex-col gap-3 max-h-[80vh] overflow-y-auto">
          <h2 className="text-xl font-bold mb-3">Polls</h2>
          {polls.length === 0 && (
            <p className="text-gray-500">No active polls</p>
          )}
          {polls.map((p) => (
            <div
              key={p.id}
              id={`poll-${p.id}`}
              className={`p-3 border rounded-md cursor-pointer ${
                selectedPoll?.id === p.id
                  ? "border-blue-500 bg-blue-50"
                  : "border-gray-200"
              }`}
              onClick={() => setSelectedPoll(p)}
            >
              <div className="font-semibold">{p.title}</div>
              <div className="text-sm text-gray-500">
                {p.options.reduce((sum, o) => sum + o.voteCount, 0)} votes
              </div>
            </div>
          ))}
        </div>

        {/* RIGHT COLUMN: Selected Poll + Posts */}
        <div className="md:col-span-2 flex flex-col gap-6">
          {/* SELECTED POLL */}
          {selectedPoll && (
            <div className="bg-white p-6 rounded-xl shadow border relative">
              <h2 className="text-xl font-bold mb-3">{selectedPoll.title}</h2>
              <p className="text-gray-600">{selectedPoll.description}</p>

              {isAdmin && (
                <div className="absolute top-4 right-4 flex gap-2">
                  <button
                    onClick={() => navigate(`/edit-poll/${selectedPoll.id}`)}
                    className="text-blue-600"
                  >
                    <AiOutlineEdit size={20} />
                  </button>
                  <button
                    onClick={async () => {
                      if (!window.confirm("Delete this poll?")) return;
                      try {
                        await axios.delete(`/api/polls/${selectedPoll.id}`, {
                          headers,
                        });
                        toast.success("Poll deleted");
                        setPolls(polls.filter((p) => p.id !== selectedPoll.id));
                        setSelectedPoll(polls[0] || null);
                      } catch {
                        toast.error("Failed to delete poll");
                      }
                    }}
                    className="text-red-600"
                  >
                    <AiOutlineDelete size={20} />
                  </button>
                </div>
              )}

              {selectedPoll.options.map((opt) => {
                const total = selectedPoll.options.reduce(
                  (sum, o) => sum + o.voteCount,
                  0
                );
                const percent = total
                  ? Math.round((opt.voteCount / total) * 100)
                  : 0;
                const alreadyVoted = Boolean(selectedPoll.userVoteOptionId);

                return (
                  <div
                    key={opt.id}
                    onClick={() => !alreadyVoted && setSelectedOption(opt.id)}
                    className={`mt-3 p-3 border rounded-md cursor-pointer ${
                      alreadyVoted
                        ? "bg-gray-100"
                        : selectedOption === opt.id
                        ? "bg-blue-100 border-blue-400"
                        : "bg-gray-50"
                    }`}
                  >
                    <div className="font-medium">{opt.text}</div>
                    {alreadyVoted && (
                      <div className="mt-2">
                        <div className="text-xs mb-1">{percent}%</div>
                        <div className="w-full h-3 bg-gray-300 rounded-full overflow-hidden">
                          <div
                            className="bg-blue-600 h-full"
                            style={{ width: `${percent}%` }}
                          ></div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}

              {!selectedPoll.userVoteOptionId && !hasVoted && (
                <button
                  onClick={submitVote}
                  disabled={!selectedOption}
                  className="w-full mt-4 px-4 py-2 bg-blue-600 text-white rounded-md disabled:opacity-40"
                >
                  Submit Vote
                </button>
              )}
            </div>
          )}

          {/* POSTS */}
          {posts.map((post) => {
            const userIsOwner =
              Number(post.user?.id) === Number(currentUser.id);
            return (
              <div
                key={post.id}
                id={`post-${post.id}`}
                className={`p-5 bg-white rounded-xl shadow border ${
                  post.pinned ? "border-blue-400" : "border-gray-200"
                }`}
              >
                {post.pinned && (
                  <div className="text-blue-600 font-semibold text-sm mb-2">
                    📌 Pinned by Admin
                  </div>
                )}
                <div className="flex justify-between">
                  <div className="flex items-center gap-3">
                    <img
                      src={post.user?.avatarUrl || "/default-avatar.png"}
                      className="w-10 h-10 rounded-full object-cover"
                    />
                    <div>
                      <div className="font-semibold">{post.user?.name}</div>
                      <div className="text-gray-500 text-sm">
                        {timeAgo(post.createdAt)}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    {userIsOwner && (
                      <button
                        onClick={() => navigate(`/edit-post/${post.id}`)}
                        className="text-blue-600"
                      >
                        <AiOutlineEdit size={20} />
                      </button>
                    )}
                    {(userIsOwner || isAdmin) && (
                      <button
                        onClick={() => handleDelete(post.id)}
                        className="text-red-600"
                      >
                        <AiOutlineDelete size={20} />
                      </button>
                    )}
                    {isAdmin && (
                      <button
                        onClick={() => togglePin(post.id)}
                        className="px-2 py-1 text-xs bg-yellow-500 text-white rounded-md"
                      >
                        {post.pinned ? "Unpin" : "Pin"}
                      </button>
                    )}
                  </div>
                </div>

                <p className="mt-3 whitespace-pre-line">{post.content}</p>
                {post.imageUrl && (
                  <img
                    src={post.imageUrl}
                    className="mt-3 rounded-lg max-h-60 object-cover w-full"
                  />
                )}

                <div className="mt-3 flex gap-4 text-sm">
                  <button onClick={() => toggleLike(post.id)}>
                    👍 {post.likeCount}
                  </button>
                  <Link to={`/post/${post.id}/replies`}>
                    💬 Replies ({post.replyCount})
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default HomePage;
