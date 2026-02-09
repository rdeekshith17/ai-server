import { useState, useEffect } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import axios from "axios";
import { 
  LayoutDashboard, 
  Building2, 
  Users, 
  Camera, 
  AlertTriangle, 
  Settings,
  Activity,
  Shield,
  LogOut,
  ChevronDown,
  Cpu,
  BarChart3,
  Bell,
  Server
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "../components/ui/avatar";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem("session_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const adminNavItems = [
  { path: "/admin", icon: LayoutDashboard, label: "Dashboard", end: true },
  { path: "/admin/clients", icon: Building2, label: "Clients" },
  { path: "/admin/users", icon: Users, label: "Users" },
  { path: "/admin/cameras", icon: Camera, label: "Cameras" },
  { path: "/admin/edge-devices", icon: Server, label: "Edge Devices" },
  { path: "/admin/incidents", icon: AlertTriangle, label: "Incidents" },
  { path: "/admin/ai-control", icon: Cpu, label: "AI Control" },
  { path: "/admin/alerts", icon: Bell, label: "Alerts" },
  { path: "/admin/analytics", icon: BarChart3, label: "Analytics" },
  { path: "/admin/settings", icon: Settings, label: "Settings" },
];

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [systemHealth, setSystemHealth] = useState(null);

  useEffect(() => {
    fetchSystemHealth();
    const interval = setInterval(fetchSystemHealth, 60000);
    return () => clearInterval(interval);
  }, []);

  const fetchSystemHealth = async () => {
    try {
      const response = await axios.get(`${API}/admin/system/health`, { 
        withCredentials: true,
        headers: getAuthHeaders()
      });
      setSystemHealth(response.data);
    } catch (error) {
      console.error("Failed to fetch system health:", error);
    }
  };

  const handleLogout = async () => {
    await logout();
  };

  const getInitials = (name) => {
    if (!name) return "U";
    return name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2);
  };

  return (
    <div className="flex h-screen" data-testid="admin-layout">
      {/* Sidebar */}
      <aside className="sidebar w-64 flex flex-col" data-testid="admin-sidebar">
        {/* Logo */}
        <div className="p-6 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-md bg-red-600/20 border border-red-600/30">
              <Shield className="w-6 h-6 text-red-500" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                SECUREGUARD
              </h1>
              <p className="text-xs text-red-400 uppercase tracking-widest">
                Admin Console
              </p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1" data-testid="admin-nav">
          {adminNavItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.end}
              className={({ isActive }) =>
                `sidebar-link ${isActive ? "active" : ""}`
              }
              data-testid={`admin-nav-${item.label.toLowerCase().replace(" ", "-")}`}
            >
              <item.icon className="w-5 h-5" />
              <span style={{ fontFamily: 'Rajdhani, sans-serif', fontWeight: 500 }}>
                {item.label}
              </span>
            </NavLink>
          ))}
          
          <div className="pt-4 border-t border-white/5 mt-4">
            <NavLink
              to="/"
              className="sidebar-link text-cyan-400"
              data-testid="switch-to-client"
            >
              <LayoutDashboard className="w-5 h-5" />
              <span style={{ fontFamily: 'Rajdhani, sans-serif', fontWeight: 500 }}>
                Client View
              </span>
            </NavLink>
          </div>
        </nav>

        {/* System Status */}
        <div className="p-4 border-t border-white/5 space-y-2">
          <p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-2">System Status</p>
          
          <div className="flex items-center gap-2 p-2 rounded-md bg-emerald-500/10 border border-emerald-500/20">
            <div className={`w-2 h-2 rounded-full ${systemHealth?.status === "operational" ? "bg-emerald-400 animate-pulse" : "bg-red-400"}`} />
            <span className="text-[10px] text-emerald-400 uppercase tracking-wider">
              {systemHealth?.status || "Loading..."}
            </span>
          </div>
          
          <div className="flex items-center gap-2 p-2 rounded-md bg-blue-500/10 border border-blue-500/20">
            <Activity className="w-3 h-3 text-blue-400" />
            <span className="text-[10px] text-blue-400 uppercase tracking-wider">
              {systemHealth?.active_streams || 0} Active Streams
            </span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-16 border-b border-white/5 flex items-center justify-between px-6 bg-card/30">
          <div className="flex items-center gap-4">
            <span className="text-xs px-2 py-1 rounded bg-red-500/20 text-red-400 border border-red-500/30 uppercase tracking-wider">
              Super Admin
            </span>
          </div>
          
          <DropdownMenu>
            <DropdownMenuTrigger className="flex items-center gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors">
              <Avatar className="h-8 w-8">
                <AvatarImage src={user?.picture} alt={user?.name} />
                <AvatarFallback className="bg-blue-600/20 text-blue-400 text-sm">
                  {getInitials(user?.name)}
                </AvatarFallback>
              </Avatar>
              <div className="text-left hidden sm:block">
                <p className="text-sm font-medium">{user?.name}</p>
                <p className="text-xs text-muted-foreground">{user?.email}</p>
              </div>
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>My Account</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => navigate("/admin/settings")}>
                <Settings className="mr-2 h-4 w-4" />
                Settings
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="text-red-400">
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-auto bg-background">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
