import { NavLink, Outlet } from "react-router-dom";
import { 
  LayoutDashboard, 
  Upload, 
  AlertTriangle, 
  BarChart3, 
  Shield,
  Cpu,
  Users
} from "lucide-react";

const navItems = [
  { path: "/", icon: LayoutDashboard, label: "Dashboard" },
  { path: "/upload", icon: Upload, label: "Upload Video" },
  { path: "/watchlist", icon: Users, label: "Watchlist" },
  { path: "/incidents", icon: AlertTriangle, label: "Incidents" },
  { path: "/analytics", icon: BarChart3, label: "Analytics" },
];

export default function Layout() {
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
                AI Detection
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
      <main className="flex-1 overflow-auto bg-background">
        <Outlet />
      </main>
    </div>
  );
}
