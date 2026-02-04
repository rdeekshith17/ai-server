import { useState, useEffect, createContext, useContext } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import { Loader2 } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Configure axios to include token from localStorage
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem("session_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auth Context
const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    // Skip auth check if we're on the callback or login page
    if (location.pathname === "/auth/callback" || location.pathname === "/login") {
      setLoading(false);
      return;
    }

    // Check if user data was passed from AuthCallback or Login
    if (location.state?.user) {
      setUser(location.state.user);
      setLoading(false);
      // Clear the state to prevent issues with refresh
      window.history.replaceState({}, document.title);
      return;
    }

    // Check authentication status
    const checkAuth = async () => {
      try {
        const response = await axios.get(`${API}/auth/me`, { withCredentials: true });
        if (response.data.success && response.data.user) {
          setUser(response.data.user);
        } else {
          setUser(null);
          // Clear invalid token
          localStorage.removeItem("session_token");
        }
      } catch (error) {
        console.error("Auth check failed:", error);
        setUser(null);
        // Clear invalid token
        localStorage.removeItem("session_token");
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [location.pathname, location.state]);

  const logout = async () => {
    try {
      await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
    } catch (error) {
      console.error("Logout error:", error);
    }
    // Clear token from localStorage
    localStorage.removeItem("session_token");
    setUser(null);
    navigate("/login", { replace: true });
  };

  const value = {
    user,
    loading,
    isAuthenticated: !!user,
    isAdmin: user?.role === "super_admin",
    logout,
    setUser
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// Protected Route Component
export function ProtectedRoute({ children, requireAdmin = false }) {
  const { user, loading, isAuthenticated, isAdmin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!loading) {
      if (!isAuthenticated) {
        navigate("/login", { replace: true, state: { from: location } });
      } else if (requireAdmin && !isAdmin) {
        navigate("/", { replace: true });
      }
    }
  }, [loading, isAuthenticated, isAdmin, requireAdmin, navigate, location]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background" data-testid="auth-loading">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
      </div>
    );
  }

  if (!isAuthenticated || (requireAdmin && !isAdmin)) {
    return null;
  }

  return children;
}

// Hook to check permissions
export function usePermission(permission) {
  const { user } = useAuth();
  if (!user || !user.permissions) return false;
  return user.permissions[permission] === true;
}
