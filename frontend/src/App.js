import { BrowserRouter, Routes, Route, useLocation } from "react-router-dom";
import "@/App.css";
import Layout from "./components/Layout";
import AdminLayout from "./components/AdminLayout";
import Dashboard from "./pages/Dashboard";
import VideoUpload from "./pages/VideoUpload";
import Incidents from "./pages/Incidents";
import Analytics from "./pages/Analytics";
import Watchlist from "./pages/Watchlist";
import LiveFeed from "./pages/LiveFeed";
import Login from "./pages/Login";
import AuthCallback from "./pages/AuthCallback";
import AdminDashboard from "./pages/admin/AdminDashboard";
import AdminClients from "./pages/admin/AdminClients";
import AdminCameras from "./pages/admin/AdminCameras";
import AdminUsers from "./pages/admin/AdminUsers";
import AdminAIControl from "./pages/admin/AdminAIControl";
import AdminAlerts from "./pages/admin/AdminAlerts";
import AdminEdgeDevices from "./pages/admin/AdminEdgeDevices";
import { Toaster } from "./components/ui/sonner";
import { AuthProvider, ProtectedRoute } from "./context/AuthContext";

// Component to handle session_id detection in URL
function AppRouter() {
  const location = useLocation();
  
  // Check URL fragment for session_id synchronously during render (prevents race conditions)
  // This MUST be detected during render, NOT in useEffect
  if (location.hash?.includes('session_id=')) {
    return <AuthCallback />;
  }
  
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      
      {/* Protected Client Routes */}
      <Route 
        path="/" 
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="upload" element={<VideoUpload />} />
        <Route path="live" element={<LiveFeed />} />
        <Route path="watchlist" element={<Watchlist />} />
        <Route path="incidents" element={<Incidents />} />
        <Route path="analytics" element={<Analytics />} />
      </Route>
      
      {/* Protected Admin Routes */}
      <Route 
        path="/admin" 
        element={
          <ProtectedRoute requireAdmin>
            <AdminLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<AdminDashboard />} />
        <Route path="clients" element={<AdminClients />} />
        <Route path="users" element={<AdminUsers />} />
        <Route path="cameras" element={<AdminCameras />} />
        <Route path="edge-devices" element={<AdminEdgeDevices />} />
        <Route path="incidents" element={<Incidents />} />
        <Route path="ai-control" element={<AdminAIControl />} />
        <Route path="alerts" element={<AdminAlerts />} />
        <Route path="analytics" element={<Analytics />} />
      </Route>
    </Routes>
  );
}

function App() {
  return (
    <div className="App noise-overlay">
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
        </AuthProvider>
      </BrowserRouter>
      <Toaster position="top-right" theme="dark" />
    </div>
  );
}

export default App;
