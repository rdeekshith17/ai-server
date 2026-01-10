import { NavLink, Outlet } from "react-router-dom";
import { 
  LayoutDashboard, 
  Upload, 
  AlertTriangle, 
  BarChart3, 
  Shield,
  Cpu
} from "lucide-react";

const navItems = [
  { path: "/", icon: LayoutDashboard, label: "Dashboard" },
  { path: "/upload", icon: Upload, label: "Upload Video" },
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

        {/* AI Status */}
        <div className="p-4 border-t border-white/5">
          <div className="flex items-center gap-3 p-3 rounded-md bg-cyan-500/10 border border-cyan-500/20">
            <Cpu className="w-5 h-5 text-cyan-400" />
            <div>
              <p className="text-xs text-cyan-400 font-medium uppercase tracking-wider">
                AI System
              </p>
              <p className="text-xs text-muted-foreground">GPT-5.2 Vision Active</p>
            </div>
            <div className="ml-auto w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
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
