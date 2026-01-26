import { useState, useEffect } from "react";
import axios from "axios";
import { 
  Building2, 
  Users, 
  Camera, 
  AlertTriangle, 
  TrendingUp,
  Activity,
  DollarSign,
  ShieldAlert,
  RefreshCw
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { ScrollArea } from "../../components/ui/scroll-area";
import { Button } from "../../components/ui/button";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const StatCard = ({ icon: Icon, label, value, subValue, color, trend }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className="stat-card card-hover"
    data-testid={`admin-stat-${label.toLowerCase().replace(/\s+/g, '-')}`}
  >
    <div className="flex items-start justify-between">
      <div>
        <p className="stat-value" style={{ color }}>{value}</p>
        <p className="stat-label">{label}</p>
        {subValue && (
          <p className="text-xs text-muted-foreground mt-1">{subValue}</p>
        )}
      </div>
      <div 
        className="p-3 rounded-md" 
        style={{ backgroundColor: `${color}15`, border: `1px solid ${color}30` }}
      >
        <Icon className="w-6 h-6" style={{ color }} />
      </div>
    </div>
    {trend !== undefined && (
      <div className="flex items-center gap-1 mt-3 text-xs">
        <TrendingUp className="w-3 h-3 text-emerald-500" />
        <span className="text-emerald-500">+{trend}%</span>
        <span className="text-muted-foreground">this month</span>
      </div>
    )}
  </motion.div>
);

const ClientRow = ({ client }) => {
  const statusColors = {
    active: { bg: "bg-emerald-500/10", text: "text-emerald-500", border: "border-emerald-500/30" },
    trial: { bg: "bg-cyan-500/10", text: "text-cyan-500", border: "border-cyan-500/30" },
    suspended: { bg: "bg-red-500/10", text: "text-red-500", border: "border-red-500/30" },
    cancelled: { bg: "bg-gray-500/10", text: "text-gray-500", border: "border-gray-500/30" }
  };
  
  const colors = statusColors[client.status] || statusColors.active;
  
  return (
    <div 
      className="flex items-center gap-4 p-4 border-b border-white/5 hover:bg-white/[0.02] transition-colors"
      data-testid={`client-row-${client.client_id}`}
    >
      <div className="p-2 rounded-md bg-blue-500/10 border border-blue-500/30">
        <Building2 className="w-4 h-4 text-blue-500" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{client.name}</p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{client.cameras_count || 0} cameras</span>
          <span>•</span>
          <span>{client.users_count || 0} users</span>
        </div>
      </div>
      <Badge 
        variant="outline" 
        className={`${colors.bg} ${colors.text} ${colors.border} uppercase text-[10px] tracking-wider`}
      >
        {client.status}
      </Badge>
      <span className="text-xs text-muted-foreground">
        {client.subscription?.plan || 'trial'}
      </span>
    </div>
  );
};

const IncidentRow = ({ incident }) => {
  const severityColors = {
    critical: { bg: "bg-red-500/10", text: "text-red-500", border: "border-red-500/30" },
    warning: { bg: "bg-amber-500/10", text: "text-amber-500", border: "border-amber-500/30" }
  };
  
  const colors = severityColors[incident.severity] || severityColors.warning;
  
  return (
    <div className="flex items-center gap-4 p-4 border-b border-white/5 hover:bg-white/[0.02] transition-colors">
      <div className={`p-2 rounded-md ${colors.bg} border ${colors.border}`}>
        <AlertTriangle className={`w-4 h-4 ${colors.text}`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{incident.description?.slice(0, 50)}...</p>
        <p className="text-xs text-muted-foreground">{incident.client_name || 'Unknown Client'}</p>
      </div>
      <Badge 
        variant="outline" 
        className={`${colors.bg} ${colors.text} ${colors.border} uppercase text-[10px] tracking-wider`}
      >
        {incident.severity}
      </Badge>
    </div>
  );
};

export default function AdminDashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [clients, setClients] = useState([]);
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [statsRes, clientsRes, incidentsRes] = await Promise.all([
        axios.get(`${API}/admin/dashboard/stats`, { withCredentials: true }),
        axios.get(`${API}/admin/clients?limit=5`, { withCredentials: true }),
        axios.get(`${API}/admin/incidents/recent?limit=5`, { withCredentials: true })
      ]);
      
      setStats(statsRes.data);
      setClients(clientsRes.data.clients || []);
      setIncidents(incidentsRes.data.incidents || []);
    } catch (error) {
      console.error("Failed to fetch dashboard data:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    fetchDashboardData();
  };

  if (loading) {
    return (
      <div className="p-6 space-y-6" data-testid="admin-dashboard-loading">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="stat-card">
              <div className="skeleton h-12 w-24 mb-2" />
              <div className="skeleton h-4 w-32" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="admin-dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            ADMIN DASHBOARD
          </h1>
          <p className="text-muted-foreground flex items-center gap-2 mt-1">
            <Activity className="w-4 h-4 text-emerald-400" />
            <span className="text-emerald-400 text-sm">All Systems Operational</span>
            <span className="text-xs">• Welcome back, {user?.name}</span>
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          disabled={refreshing}
          className="flex items-center gap-2"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard 
          icon={Building2} 
          label="Total Clients" 
          value={stats?.total_clients || 0}
          subValue={`${stats?.active_clients || 0} active, ${stats?.trial_clients || 0} trial`}
          color="#3b82f6"
        />
        <StatCard 
          icon={Camera} 
          label="Total Cameras" 
          value={stats?.total_cameras || 0}
          subValue={`${stats?.online_cameras || 0} online`}
          color="#06b6d4"
        />
        <StatCard 
          icon={ShieldAlert} 
          label="Incidents (24h)" 
          value={stats?.total_incidents_24h || 0}
          subValue={`${stats?.critical_incidents_24h || 0} critical`}
          color="#f59e0b"
        />
        <StatCard 
          icon={DollarSign} 
          label="Monthly Revenue" 
          value={`$${((stats?.monthly_revenue_cents || 0) / 100).toLocaleString()}`}
          color="#10b981"
        />
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Clients */}
        <Card className="bg-card/50 border-white/5" data-testid="admin-recent-clients">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-lg" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
              <Building2 className="w-5 h-5 text-blue-500" />
              RECENT CLIENTS
            </CardTitle>
            <Link 
              to="/admin/clients"
              className="text-xs text-cyan-400 hover:underline"
            >
              View All
            </Link>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[300px]">
              {clients.length > 0 ? (
                clients.map((client) => (
                  <ClientRow key={client.client_id} client={client} />
                ))
              ) : (
                <div className="p-8 text-center text-muted-foreground">
                  <Building2 className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>No clients yet</p>
                  <Link to="/admin/clients" className="text-cyan-400 text-sm hover:underline">
                    Add your first client
                  </Link>
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Recent Incidents */}
        <Card className="bg-card/50 border-white/5" data-testid="admin-recent-incidents">
          <CardHeader className="pb-3 flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-lg" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              RECENT INCIDENTS
            </CardTitle>
            <Link 
              to="/admin/incidents"
              className="text-xs text-cyan-400 hover:underline"
            >
              View All
            </Link>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[300px]">
              {incidents.length > 0 ? (
                incidents.map((incident, idx) => (
                  <IncidentRow key={incident.id || idx} incident={incident} />
                ))
              ) : (
                <div className="p-8 text-center text-muted-foreground">
                  <AlertTriangle className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>No incidents in the last 24 hours</p>
                  <p className="text-xs mt-1">All systems are running smoothly</p>
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="bg-card/50 border-white/5" data-testid="admin-quick-actions">
        <CardContent className="p-6">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h3 className="text-lg font-semibold" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                QUICK ACTIONS
              </h3>
              <p className="text-sm text-muted-foreground">
                Manage your platform
              </p>
            </div>
            <div className="flex gap-3">
              <Link 
                to="/admin/clients" 
                className="px-4 py-2 rounded-sm bg-blue-500/20 border border-blue-500/50 text-blue-400 flex items-center gap-2 hover:bg-blue-500/30 transition-colors"
                data-testid="add-client-btn"
              >
                <Building2 className="w-4 h-4" />
                Add Client
              </Link>
              <Link 
                to="/admin/cameras" 
                className="px-4 py-2 rounded-sm bg-cyan-500/20 border border-cyan-500/50 text-cyan-400 flex items-center gap-2 hover:bg-cyan-500/30 transition-colors"
                data-testid="manage-cameras-btn"
              >
                <Camera className="w-4 h-4" />
                Manage Cameras
              </Link>
              <Link 
                to="/admin/ai-control" 
                className="btn-primary flex items-center gap-2"
                data-testid="ai-control-btn"
              >
                <Activity className="w-4 h-4" />
                AI Control
              </Link>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
