import { useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import { Shield, Loader2 } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * AuthCallback - Processes OAuth callback from Emergent Auth
 * REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
 */
export default function AuthCallback() {
  const navigate = useNavigate();
  const location = useLocation();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Prevent double processing in StrictMode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processSession = async () => {
      try {
        // Extract session_id from URL hash
        const hash = window.location.hash;
        const sessionIdMatch = hash.match(/session_id=([^&]+)/);
        
        if (!sessionIdMatch) {
          console.error("No session_id found in URL");
          navigate("/login", { replace: true });
          return;
        }

        const sessionId = sessionIdMatch[1];

        // Exchange session_id for session_token
        const response = await axios.post(
          `${API}/auth/session`,
          { session_id: sessionId },
          { withCredentials: true }
        );

        if (response.data.success && response.data.user) {
          // Clear the hash from URL
          window.history.replaceState(null, "", window.location.pathname);
          
          // Navigate to appropriate dashboard based on role
          const user = response.data.user;
          if (user.role === "super_admin") {
            navigate("/admin", { replace: true, state: { user } });
          } else {
            navigate("/", { replace: true, state: { user } });
          }
        } else {
          console.error("Auth failed:", response.data.message);
          navigate("/login", { replace: true });
        }
      } catch (error) {
        console.error("Auth callback error:", error);
        navigate("/login", { replace: true });
      }
    };

    processSession();
  }, [navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-background" data-testid="auth-callback">
      <div className="text-center">
        <div className="p-4 rounded-lg bg-blue-600/20 border border-blue-600/30 inline-block mb-6">
          <Shield className="w-12 h-12 text-blue-500" />
        </div>
        <div className="flex items-center gap-3 justify-center">
          <Loader2 className="w-5 h-5 animate-spin text-cyan-400" />
          <span className="text-lg text-muted-foreground">Authenticating...</span>
        </div>
      </div>
    </div>
  );
}
