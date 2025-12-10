import axios from "axios";

// Change this to your deployed backend URL
const api = axios.create({
  baseURL: "https://appraisal-1lzx.onrender.com", // no /api
});

// Attach JWT token automatically if available
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

export default api;
