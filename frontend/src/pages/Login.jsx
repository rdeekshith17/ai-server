import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { Shield, LogIn, Camera, AlertTriangle, BarChart3, Users, Loader2, Mail, Lock, User } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { motion } from "framer-motion";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Login Page - SecureGuard Multi-Tenant Platform
 * Supports both email/password and Google OAuth login
 */
export default function Login() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [loggingIn, setLoggingIn] = useState(false);
  const [isRegister, setIsRegister] = useState(false);
  
  // Form state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    // Check if already authenticated
    const checkAuth = async () => {
      try {
        // Check for token in localStorage
        const token = localStorage.getItem("session_token");
        const headers = token ? { Authorization: `Bearer ${token}` } : {};
        
        const response = await axios.get(`${API}/auth/me`, { 
          withCredentials: true,
          headers
        });
        if (response.data.success && response.data.user) {
          // User is already authenticated, redirect based on role
          const user = response.data.user;
          if (user.role === "super_admin") {
            navigate("/admin", { replace: true });
          } else {
            navigate("/", { replace: true });
          }
          return;
        }
      } catch (error) {
        // Not authenticated, show login page
      }
      setLoading(false);
    };

    checkAuth();
  }, [navigate]);

  const handleEmailLogin = async (e) => {
    e.preventDefault();
    setError("");
    setLoggingIn(true);

    try {
      const endpoint = isRegister ? "/auth/register" : "/auth/login";
      const payload = isRegister 
        ? { email, password, name }
        : { email, password };

      const response = await axios.post(`${API}${endpoint}`, payload, {
        withCredentials: true
      });

      if (response.data.success && response.data.user) {
        // Store token in localStorage for cross-origin requests
        if (response.data.token) {
          localStorage.setItem("session_token", response.data.token);
        }
        
        toast.success(isRegister ? "Account created!" : "Welcome back!");
        
        const user = response.data.user;
        if (user.role === "super_admin") {
          navigate("/admin", { replace: true, state: { user } });
        } else {
          navigate("/", { replace: true, state: { user } });
        }
      } else {
        setError(response.data.message || "Authentication failed");
      }
    } catch (error) {
      console.error("Auth error:", error);
      setError(error.response?.data?.message || "Authentication failed. Please try again.");
    } finally {
      setLoggingIn(false);
    }
  };

  const handleGoogleLogin = () => {
    setLoggingIn(true);
    const redirectUrl = window.location.origin + '/auth/callback';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background" data-testid="login-loading">
        <Loader2 className="w-8 h-8 animate-spin text-cyan-400" />
      </div>
    );
  }

  return (
    <div className="min-h-screen flex bg-background" data-testid="login-page">
      {/* Left Side - Branding */}
      <div className="hidden lg:flex lg:w-1/2 relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        {/* Background pattern */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute inset-0" style={{
            backgroundImage: `radial-gradient(circle at 25px 25px, rgba(59, 130, 246, 0.15) 2px, transparent 0)`,
            backgroundSize: '50px 50px'
          }} />
        </div>
        
        {/* Content */}
        <div className="relative z-10 p-12 flex flex-col justify-between w-full">
          <div>
            <div className="flex items-center gap-3 mb-12">
              <div className="p-3 rounded-md bg-blue-600/20 border border-blue-600/30">
                <Shield className="w-8 h-8 text-blue-500" />
              </div>
              <div>
                <h1 className="text-2xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                  SECUREGUARD
                </h1>
                <p className="text-xs text-muted-foreground uppercase tracking-widest">
                  AI-Powered Retail Security
                </p>
              </div>
            </div>

            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
            >
              <h2 className="text-4xl font-bold mb-4" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                Enterprise Shoplifting Detection Platform
              </h2>
              <p className="text-lg text-muted-foreground mb-8">
                Multi-layered AI detection powered by YOLO, DeepFace, Pose Estimation, and GPT-5.2 Vision
              </p>
            </motion.div>
          </div>

          {/* Features */}
          <div className="grid grid-cols-2 gap-4">
            <motion.div 
              className="p-4 rounded-lg bg-white/5 border border-white/10"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 }}
            >
              <Camera className="w-8 h-8 text-cyan-400 mb-3" />
              <h3 className="font-semibold mb-1">Live Detection</h3>
              <p className="text-sm text-muted-foreground">Real-time monitoring with RTSP streams</p>
            </motion.div>
            
            <motion.div 
              className="p-4 rounded-lg bg-white/5 border border-white/10"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 }}
            >
              <AlertTriangle className="w-8 h-8 text-amber-400 mb-3" />
              <h3 className="font-semibold mb-1">Instant Alerts</h3>
              <p className="text-sm text-muted-foreground">Critical incident notifications</p>
            </motion.div>
            
            <motion.div 
              className="p-4 rounded-lg bg-white/5 border border-white/10"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 }}
            >
              <Users className="w-8 h-8 text-purple-400 mb-3" />
              <h3 className="font-semibold mb-1">Watchlist</h3>
              <p className="text-sm text-muted-foreground">Face recognition for known offenders</p>
            </motion.div>
            
            <motion.div 
              className="p-4 rounded-lg bg-white/5 border border-white/10"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.6 }}
            >
              <BarChart3 className="w-8 h-8 text-emerald-400 mb-3" />
              <h3 className="font-semibold mb-1">Analytics</h3>
              <p className="text-sm text-muted-foreground">Comprehensive incident reporting</p>
            </motion.div>
          </div>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="flex-1 flex items-center justify-center p-8">
        <motion.div 
          className="w-full max-w-md"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center gap-3 mb-8 justify-center">
            <div className="p-3 rounded-md bg-blue-600/20 border border-blue-600/30">
              <Shield className="w-8 h-8 text-blue-500" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                SECUREGUARD
              </h1>
            </div>
          </div>

          <div className="bg-card/50 border border-white/10 rounded-lg p-8">
            <div className="text-center mb-6">
              <h2 className="text-2xl font-bold mb-2" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                {isRegister ? "Create Account" : "Welcome Back"}
              </h2>
              <p className="text-muted-foreground">
                {isRegister ? "Sign up to get started" : "Sign in to access your security dashboard"}
              </p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mb-4 p-3 rounded-md bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                {error}
              </div>
            )}

            {/* Email/Password Form */}
            <form onSubmit={handleEmailLogin} className="space-y-4">
              {isRegister && (
                <div className="space-y-2">
                  <Label htmlFor="name">Full Name</Label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      id="name"
                      type="text"
                      placeholder="John Doe"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      className="pl-10"
                      required={isRegister}
                      data-testid="register-name-input"
                    />
                  </div>
                </div>
              )}
              
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="email"
                    type="email"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="pl-10"
                    required
                    data-testid="login-email-input"
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-10"
                    required
                    minLength={6}
                    data-testid="login-password-input"
                  />
                </div>
              </div>

              <Button
                type="submit"
                disabled={loggingIn}
                className="w-full h-11 bg-blue-600 hover:bg-blue-700"
                data-testid="login-submit-btn"
              >
                {loggingIn ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <>
                    <LogIn className="w-4 h-4 mr-2" />
                    {isRegister ? "Create Account" : "Sign In"}
                  </>
                )}
              </Button>
            </form>

            {/* Divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-white/10"></div>
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-card px-2 text-muted-foreground">Or continue with</span>
              </div>
            </div>

            {/* Google Login */}
            <Button
              onClick={handleGoogleLogin}
              disabled={loggingIn}
              variant="outline"
              className="w-full h-11 bg-white/5 hover:bg-white/10 border-white/10"
              data-testid="google-login-btn"
            >
              <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24">
                <path
                  fill="#4285F4"
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                />
                <path
                  fill="#34A853"
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                />
                <path
                  fill="#FBBC05"
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                />
                <path
                  fill="#EA4335"
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                />
              </svg>
              Google
            </Button>

            {/* Toggle Register/Login */}
            <div className="mt-6 text-center text-sm">
              <span className="text-muted-foreground">
                {isRegister ? "Already have an account?" : "Don't have an account?"}
              </span>
              <button
                type="button"
                onClick={() => {
                  setIsRegister(!isRegister);
                  setError("");
                }}
                className="ml-2 text-cyan-400 hover:underline"
                data-testid="toggle-auth-mode"
              >
                {isRegister ? "Sign in" : "Create one"}
              </button>
            </div>
          </div>

          {/* Demo Notice */}
          <div className="mt-6 p-4 rounded-lg bg-amber-500/10 border border-amber-500/30 text-center">
            <p className="text-sm text-amber-400">
              First user to sign up becomes the Super Admin
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
