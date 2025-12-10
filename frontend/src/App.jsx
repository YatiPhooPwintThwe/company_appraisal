import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useParams,
} from "react-router-dom";
import LoginPage from "./pages/LoginPage.jsx";
import HomePage from "./pages/HomePage.jsx";
import CreatePostPage from "./pages/CreatePostPage.jsx";
import EditPostPage from "./pages/EditPostPage.jsx";
import { Toaster } from "react-hot-toast";
import ReplyPage from "./pages/ReplyPage.jsx";
import CreatePollPage from "./pages/CreatePollPage.jsx";
import EditPollPage from "./pages/EditPollPage.jsx";
import NotificationPage from "./pages/NotificationsPage.jsx";
// Protected route component
const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem("token");

  if (!token || token.trim() === "") {
    return <Navigate to="/login" replace />;
  }

  return children;
};
const RedirectPostToHome = () => {
  const { postId } = useParams();
  return <Navigate to={`/?postId=${postId}`} replace />;
};

const RedirectPollToHome = () => {
  const { pollId } = useParams();
  return <Navigate to={`/?pollId=${pollId}`} replace />;
};

function App() {
  return (
    <>
      {/* 🔥 Toasts now work because Toaster is inside JSX */}
      <Toaster position="top-center" />

      <Router>
        <Routes>
          {/* Public route */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected routes */}
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <HomePage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/create-post"
            element={
              <ProtectedRoute>
                <CreatePostPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/edit-post/:postId"
            element={
              <ProtectedRoute>
                <EditPostPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/notifications"
            element={
              <ProtectedRoute>
                <NotificationPage />
              </ProtectedRoute>
            }
          />
          {/* ✅ Reply Page (View Post + all replies) */}
          <Route
            path="/post/:id/replies"
            element={
              <ProtectedRoute>
                <ReplyPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/create-poll"
            element={
              <ProtectedRoute>
                <CreatePollPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/edit-poll/:pollId"
            element={
              <ProtectedRoute>
                <EditPollPage />
              </ProtectedRoute>
            }
          />
          <Route path="/posts/:postId" element={<RedirectPostToHome />} />

          <Route path="/polls/:pollId" element={<RedirectPollToHome />} />

          {/* Redirect unknown paths */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </>
  );
}

export default App;
