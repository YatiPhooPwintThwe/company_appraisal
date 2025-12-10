import axios from "axios";

const api = axios.create({
  baseURL: "https://appraisal-1lzx.onrender.com/api", // NO /api
});

// Attach token automatically
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
