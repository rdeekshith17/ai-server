import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { 
  LayoutDashboard, 
  Upload, 
  AlertTriangle, 
  BarChart3, 
  Shield,
  Users,
  Camera,
  Video,
  LogOut,
  ChevronDown,
  Settings,
  UserCog
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "./ui/avatar";

const navItems = [
  { path: "/", icon: LayoutDashboard, label: "Dashboard" },
  { path: "/cameras", icon: Camera, label: "Live Cameras" },
  { path: "/live", icon: Video, label: "Video Detection" },
  { path: "/upload", icon: Upload, label: "Upload Video" },
  { path: "/watchlist", icon: Users, label: "Watchlist" },
  { path: "/incidents", icon: AlertTriangle, label: "Incidents" },
  { path: "/analytics", icon: BarChart3, label: "Analytics" },
  { path: "/settings", icon: Settings, label: "Settings" },
];

export default function Layout() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
  };

  const getInitials = (name) => {
    if (!name) return "U";
    return name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2);
  };

  return (
    <div className="flex h-screen" data-testid="app-layout">
      {/* Sidebar */}
      <aside className="sidebar w-64 flex flex-col" data-testid="sidebar">
        {/* Logo */}
        <div className="p-6 border-b border-white/5">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-md bg-blue-600/20 border border-blue-600/30">
              <Shield className="w-6 h-6 text-blue-500" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                SECUREGUARD
              </h1>
              <p className="text-xs text-muted-foreground uppercase tracking-widest">
                {user?.client_name || 'AI Detection'}
              </p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4 space-y-1" data-testid="nav-menu">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) =>
                `sidebar-link ${isActive ? "active" : ""}`
              }
              data-testid={`nav-${item.label.toLowerCase().replace(" ", "-")}`}
            >
              <item.icon className="w-5 h-5" />
              <span style={{ fontFamily: 'Rajdhani, sans-serif', fontWeight: 500 }}>
                {item.label}
              </span>
            </NavLink>
          ))}
          
          {/* Admin Link - Only for super_admin */}
          {isAdmin && (
            <div className="pt-4 border-t border-white/5 mt-4">
              <NavLink
                to="/admin"
                className="sidebar-link text-red-400"
                data-testid="admin-console-link"
              >
                <UserCog className="w-5 h-5" />
                <span style={{ fontFamily: 'Rajdhani, sans-serif', fontWeight: 500 }}>
                  Admin Console
                </span>
              </NavLink>
            </div>
          )}
        </nav>

        {/* ML Models Status */}
        <div className="p-4 border-t border-white/5 space-y-2">
          <p className="text-[10px] text-muted-foreground uppercase tracking-widest mb-2">ML Models</p>
          
          <div className="flex items-center gap-2 p-2 rounded-md bg-purple-500/10 border border-purple-500/20">
            <div className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
            <span className="text-[10px] text-purple-400 uppercase tracking-wider">YOLO v8</span>
          </div>
          
          <div className="flex items-center gap-2 p-2 rounded-md bg-pink-500/10 border border-pink-500/20">
            <div className="w-2 h-2 rounded-full bg-pink-400 animate-pulse" />
            <span className="text-[10px] text-pink-400 uppercase tracking-wider">DeepFace</span>
          </div>
          
          <div className="flex items-center gap-2 p-2 rounded-md bg-cyan-500/10 border border-cyan-500/20">
            <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
            <span className="text-[10px] text-cyan-400 uppercase tracking-wider">GPT-5.2</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-16 border-b border-white/5 flex items-center justify-end px-6 bg-card/30">
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
                <p className="text-xs text-muted-foreground capitalize">{user?.role?.replace('_', ' ')}</p>
              </div>
              <ChevronDown className="w-4 h-4 text-muted-foreground" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>
                <div>
                  <p>{user?.name}</p>
                  <p className="text-xs font-normal text-muted-foreground">{user?.email}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              {isAdmin && (
                <>
                  <DropdownMenuItem onClick={() => navigate("/admin")}>
                    <UserCog className="mr-2 h-4 w-4" />
                    Admin Console
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                </>
              )}
              <DropdownMenuItem onClick={() => navigate("/settings")}>
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
