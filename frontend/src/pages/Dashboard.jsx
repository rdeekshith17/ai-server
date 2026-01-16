import { useState, useEffect } from "react";
import axios from "axios";
import { 
  Video, 
  AlertTriangle, 
  ShieldAlert, 
  ShieldCheck,
  Activity,
  Clock,
  TrendingUp,
  Users,
  Camera,
  Play
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { ScrollArea } from "../components/ui/scroll-area";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const StatCard = ({ icon: Icon, label, value, trend, color }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className="stat-card card-hover"
    data-testid={`stat-${label.toLowerCase().replace(/\s+/g, '-')}`}
  >
    <div className="flex items-start justify-between">
      <div>
        <p className="stat-value" style={{ color }}>{value}</p>
        <p className="stat-label">{label}</p>
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
        <span className="text-muted-foreground">from last week</span>
      </div>
    )}
  </motion.div>
);

const IncidentRow = ({ incident }) => {
  const severityColors = {
    critical: { bg: "bg-red-500/10", text: "text-red-500", border: "border-red-500/30" },
    warning: { bg: "bg-amber-500/10", text: "text-amber-500", border: "border-amber-500/30" },
    safe: { bg: "bg-emerald-500/10", text: "text-emerald-500", border: "border-emerald-500/30" }
  };
  
  const colors = severityColors[incident.severity] || severityColors.safe;
  
  return (
    <div 
      className="flex items-center gap-4 p-4 border-b border-white/5 hover:bg-white/[0.02] transition-colors"
      data-testid={`incident-${incident.id}`}
    >
      <div className={`p-2 rounded-md ${colors.bg} border ${colors.border}`}>
        <AlertTriangle className={`w-4 h-4 ${colors.text}`} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{incident.description}</p>
        <p className="text-xs text-muted-foreground">{incident.video_name}</p>
      </div>
      <Badge 
        variant="outline" 
        className={`${colors.bg} ${colors.text} ${colors.border} uppercase text-[10px] tracking-wider`}
      >
        {incident.severity}
      </Badge>
      <span className="text-xs text-muted-foreground font-mono">
        {Math.round(incident.confidence * 100)}%
      </span>
    </div>
  );
};

const VideoRow = ({ video }) => {
  const statusColors = {
    completed: "text-emerald-500",
    processing: "text-cyan-400",
    pending: "text-amber-500",
    failed: "text-red-500"
  };
  
  return (
    <div 
      className="flex items-center gap-4 p-4 border-b border-white/5 hover:bg-white/[0.02] transition-colors"
      data-testid={`video-${video.id}`}
    >
      <div className="p-2 rounded-md bg-blue-500/10 border border-blue-500/30">
        <Video className="w-4 h-4 text-blue-500" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{video.filename}</p>
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <span>{Math.round(video.duration_seconds)}s</span>
          <span>•</span>
          <span>{video.total_frames} frames</span>
        </div>
      </div>
      <span className={`text-xs font-mono uppercase ${statusColors[video.status]}`}>
        {video.status}
      </span>
      {video.incidents_count > 0 && (
        <Badge variant="destructive" className="text-[10px]">
          {video.incidents_count} alerts
        </Badge>
      )}
    </div>
  );
};

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [watchlistStats, setWatchlistStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardStats();
    fetchWatchlistStats();
    const interval = setInterval(fetchDashboardStats, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardStats = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/stats`);
      setStats(response.data);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch dashboard stats:", err);
      setError("Failed to load dashboard data");
    } finally {
      setLoading(false);
    }
  };

  const fetchWatchlistStats = async () => {
    try {
      const response = await axios.get(`${API}/watchlist/stats/summary`);
      setWatchlistStats(response.data);
    } catch (err) {
      console.error("Failed to fetch watchlist stats:", err);
    }
  };

  if (loading) {
    return (
      <div className="p-6 space-y-6" data-testid="dashboard-loading">
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

  if (error) {
    return (
      <div className="p-6 flex items-center justify-center h-full" data-testid="dashboard-error">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
          <p className="text-lg font-medium">{error}</p>
          <button 
            onClick={fetchDashboardStats}
            className="btn-primary mt-4"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="dashboard">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            SECURITY DASHBOARD
          </h1>
          <p className="text-muted-foreground flex items-center gap-2 mt-1">
            <Activity className="w-4 h-4 text-cyan-400" />
            <span className="text-cyan-400 text-sm">System Online</span>
            <span className="text-xs">• Last updated: {new Date().toLocaleTimeString()}</span>
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="px-3 py-1.5 rounded-sm bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-mono uppercase tracking-wider">
            AI Active
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard 
          icon={Video} 
          label="Total Videos" 
          value={stats?.total_videos || 0}
          color="#3b82f6"
        />
        <StatCard 
          icon={ShieldAlert} 
          label="Critical Alerts" 
          value={stats?.critical_count || 0}
          color="#ef4444"
        />
        <StatCard 
          icon={AlertTriangle} 
          label="Warnings" 
          value={stats?.warning_count || 0}
          color="#f59e0b"
        />
        <StatCard 
          icon={ShieldCheck} 
          label="Safe Analyses" 
          value={stats?.safe_count || 0}
          color="#10b981"
        />
        <StatCard 
          icon={Users} 
          label="Watchlist" 
          value={watchlistStats?.active || 0}
          color="#8b5cf6"
        />
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Incidents */}
        <Card className="bg-card/50 border-white/5" data-testid="recent-incidents">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              RECENT INCIDENTS
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[300px]">
              {stats?.recent_incidents?.length > 0 ? (
                stats.recent_incidents.map((incident) => (
                  <IncidentRow key={incident.id} incident={incident} />
                ))
              ) : (
                <div className="p-8 text-center text-muted-foreground">
                  <ShieldCheck className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>No incidents detected</p>
                  <p className="text-xs mt-1">Upload a video to start analysis</p>
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Recent Videos */}
        <Card className="bg-card/50 border-white/5" data-testid="recent-videos">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-lg" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
              <Video className="w-5 h-5 text-blue-500" />
              RECENT VIDEOS
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[300px]">
              {stats?.recent_videos?.length > 0 ? (
                stats.recent_videos.map((video) => (
                  <VideoRow key={video.id} video={video} />
                ))
              ) : (
                <div className="p-8 text-center text-muted-foreground">
                  <Video className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>No videos uploaded</p>
                  <p className="text-xs mt-1">Upload your first video for analysis</p>
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card className="bg-card/50 border-white/5" data-testid="quick-actions">
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                QUICK ACTIONS
              </h3>
              <p className="text-sm text-muted-foreground">
                Upload security footage for AI-powered shoplifting detection
              </p>
            </div>
            <a 
              href="/upload" 
              className="btn-primary flex items-center gap-2"
              data-testid="upload-video-btn"
            >
              <Video className="w-4 h-4" />
              Upload Video
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
