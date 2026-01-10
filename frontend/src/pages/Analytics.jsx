import { useState, useEffect } from "react";
import axios from "axios";
import { 
  BarChart3, 
  PieChart, 
  TrendingUp, 
  Video,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  Target
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  PieChart as RechartsPie,
  Pie,
  Cell,
  Legend
} from "recharts";
import { motion } from "framer-motion";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const COLORS = ["#ef4444", "#f59e0b", "#10b981", "#3b82f6", "#8b5cf6", "#ec4899"];

const StatCard = ({ icon: Icon, label, value, color, subtitle }) => (
  <motion.div
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    className="stat-card card-hover"
  >
    <div className="flex items-start justify-between">
      <div>
        <p className="stat-value" style={{ color }}>{value}</p>
        <p className="stat-label">{label}</p>
        {subtitle && (
          <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
        )}
      </div>
      <div 
        className="p-3 rounded-md" 
        style={{ backgroundColor: `${color}15`, border: `1px solid ${color}30` }}
      >
        <Icon className="w-6 h-6" style={{ color }} />
      </div>
    </div>
  </motion.div>
);

export default function Analytics() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      const response = await axios.get(`${API}/analytics`);
      setAnalytics(response.data);
    } catch (err) {
      console.error("Failed to fetch analytics:", err);
    } finally {
      setLoading(false);
    }
  };

  // Transform data for charts
  const behaviorData = analytics?.incidents_by_type 
    ? Object.entries(analytics.incidents_by_type).map(([name, value]) => ({
        name: name.length > 15 ? name.substring(0, 15) + "..." : name,
        fullName: name,
        value
      }))
    : [];

  const storeData = analytics?.incidents_by_store
    ? Object.entries(analytics.incidents_by_store).map(([name, value]) => ({
        name: name.replace("_", " "),
        value
      }))
    : [];

  const severityData = [
    { name: "Critical", value: analytics?.critical_alerts || 0, color: "#ef4444" },
    { name: "Warning", value: analytics?.warnings || 0, color: "#f59e0b" },
    { name: "Safe", value: analytics?.safe_analyses || 0, color: "#10b981" },
  ].filter(d => d.value > 0);

  if (loading) {
    return (
      <div className="p-6 space-y-6" data-testid="analytics-loading">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="stat-card">
              <div className="skeleton h-12 w-24 mb-2" />
              <div className="skeleton h-4 w-32" />
            </div>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="skeleton h-[400px] rounded-lg" />
          <div className="skeleton h-[400px] rounded-lg" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="analytics-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
          ANALYTICS
        </h1>
        <p className="text-muted-foreground mt-1">
          Detection metrics and trend analysis
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard 
          icon={Video} 
          label="Total Videos" 
          value={analytics?.total_videos || 0}
          color="#3b82f6"
        />
        <StatCard 
          icon={AlertTriangle} 
          label="Total Incidents" 
          value={analytics?.total_incidents || 0}
          color="#f59e0b"
        />
        <StatCard 
          icon={Target} 
          label="Detection Rate" 
          value={`${analytics?.detection_rate || 0}%`}
          color="#8b5cf6"
          subtitle="Incidents per video"
        />
        <StatCard 
          icon={TrendingUp} 
          label="Avg Confidence" 
          value={`${analytics?.average_confidence || 0}%`}
          color="#06b6d4"
          subtitle="AI detection confidence"
        />
      </div>

      {/* Severity Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="p-3 rounded-md bg-red-500/10 border border-red-500/30">
              <ShieldAlert className="w-8 h-8 text-red-500" />
            </div>
            <div>
              <p className="text-3xl font-bold text-red-500" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                {analytics?.critical_alerts || 0}
              </p>
              <p className="text-sm text-muted-foreground uppercase tracking-wider">
                Critical Alerts
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="p-3 rounded-md bg-amber-500/10 border border-amber-500/30">
              <AlertTriangle className="w-8 h-8 text-amber-500" />
            </div>
            <div>
              <p className="text-3xl font-bold text-amber-500" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                {analytics?.warnings || 0}
              </p>
              <p className="text-sm text-muted-foreground uppercase tracking-wider">
                Warnings
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="p-3 rounded-md bg-emerald-500/10 border border-emerald-500/30">
              <ShieldCheck className="w-8 h-8 text-emerald-500" />
            </div>
            <div>
              <p className="text-3xl font-bold text-emerald-500" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                {analytics?.safe_analyses || 0}
              </p>
              <p className="text-sm text-muted-foreground uppercase tracking-wider">
                Safe Analyses
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Behavior Types Chart */}
        <Card className="bg-card/50 border-white/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
              <BarChart3 className="w-5 h-5 text-blue-500" />
              INCIDENTS BY BEHAVIOR
            </CardTitle>
          </CardHeader>
          <CardContent>
            {behaviorData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={behaviorData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis type="number" stroke="rgba(255,255,255,0.3)" fontSize={12} />
                  <YAxis 
                    dataKey="name" 
                    type="category" 
                    stroke="rgba(255,255,255,0.3)" 
                    fontSize={11}
                    width={120}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: "hsl(240 6% 10%)", 
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: "0.375rem"
                    }}
                    labelStyle={{ color: "#fff" }}
                    formatter={(value, name, props) => [value, props.payload.fullName]}
                  />
                  <Bar 
                    dataKey="value" 
                    fill="#3b82f6" 
                    radius={[0, 4, 4, 0]}
                    name="Incidents"
                  />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>No behavior data available</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Severity Distribution Chart */}
        <Card className="bg-card/50 border-white/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
              <PieChart className="w-5 h-5 text-purple-500" />
              SEVERITY DISTRIBUTION
            </CardTitle>
          </CardHeader>
          <CardContent>
            {severityData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <RechartsPie>
                  <Pie
                    data={severityData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {severityData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: "hsl(240 6% 10%)", 
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: "0.375rem"
                    }}
                  />
                  <Legend 
                    verticalAlign="bottom" 
                    height={36}
                    formatter={(value) => <span style={{ color: "#a1a1aa" }}>{value}</span>}
                  />
                </RechartsPie>
              </ResponsiveContainer>
            ) : (
              <div className="h-[300px] flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <PieChart className="w-12 h-12 mx-auto mb-3 opacity-30" />
                  <p>No severity data available</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Store Type Distribution */}
      <Card className="bg-card/50 border-white/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            <BarChart3 className="w-5 h-5 text-cyan-400" />
            INCIDENTS BY STORE TYPE
          </CardTitle>
        </CardHeader>
        <CardContent>
          {storeData.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={storeData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis 
                  dataKey="name" 
                  stroke="rgba(255,255,255,0.3)" 
                  fontSize={12}
                  style={{ textTransform: "capitalize" }}
                />
                <YAxis stroke="rgba(255,255,255,0.3)" fontSize={12} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: "hsl(240 6% 10%)", 
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "0.375rem"
                  }}
                />
                <Bar dataKey="value" fill="#06b6d4" radius={[4, 4, 0, 0]} name="Incidents" />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[250px] flex items-center justify-center text-muted-foreground">
              <div className="text-center">
                <BarChart3 className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>No store type data available</p>
                <p className="text-sm mt-1">Upload and analyze videos to see distribution</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
