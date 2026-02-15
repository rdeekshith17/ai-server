import { useState, useEffect, useRef } from "react";
import axios from "axios";
import { 
  Camera, 
  AlertTriangle, 
  User,
  Activity,
  Shield,
  RefreshCw,
  Wifi,
  WifiOff,
  Settings,
  Maximize2,
  Eye,
  Clock,
  Zap,
  Building2
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";

const API = process.env.REACT_APP_BACKEND_URL;

const getAuthHeaders = () => {
  const token = localStorage.getItem('session_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const statusColors = {
  online: { bg: "bg-emerald-500/20", border: "border-emerald-500/50", text: "text-emerald-400", dot: "bg-emerald-500" },
  degraded: { bg: "bg-amber-500/20", border: "border-amber-500/50", text: "text-amber-400", dot: "bg-amber-500" },
  offline: { bg: "bg-red-500/20", border: "border-red-500/50", text: "text-red-400", dot: "bg-red-500" }
};

export default function LiveCameras() {
  const { user } = useAuth();
  const [snapshots, setSnapshots] = useState([]);
  const [clients, setClients] = useState([]);
  const [selectedClientId, setSelectedClientId] = useState(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [selectedCamera, setSelectedCamera] = useState(null);
  const [refreshInterval, setRefreshInterval] = useState(5000);
  const refreshRef = useRef(null);

  useEffect(() => {
    if (user?.role === 'super_admin') {
      fetchClients();
    }
    fetchSnapshots();
    
    return () => {
      if (refreshRef.current) {
        clearInterval(refreshRef.current);
      }
    };
  }, [user]);

  useEffect(() => {
    if (autoRefresh && (user?.client_id || selectedClientId)) {
      refreshRef.current = setInterval(fetchSnapshots, refreshInterval);
    } else {
      if (refreshRef.current) {
        clearInterval(refreshRef.current);
      }
    }
    
    return () => {
      if (refreshRef.current) {
        clearInterval(refreshRef.current);
      }
    };
  }, [autoRefresh, refreshInterval, selectedClientId, user?.client_id]);

  const fetchClients = async () => {
    try {
      const response = await axios.get(`${API}/api/admin/clients`, {
        withCredentials: true,
        headers: getAuthHeaders()
      });
      if (response.data.clients) {
        setClients(response.data.clients);
        if (response.data.clients.length > 0 && !selectedClientId) {
          setSelectedClientId(response.data.clients[0].client_id);
        }
      }
    } catch (error) {
      console.error("Failed to fetch clients:", error);
    }
  };

  const fetchSnapshots = async () => {
    const clientId = user?.client_id || selectedClientId;
    if (!clientId) {
      setLoading(false);
      return;
    }
    
    try {
      const response = await axios.get(`${API}/api/live/snapshots/${clientId}`, {
        withCredentials: true,
        headers: getAuthHeaders()
      });
      
      if (response.data.snapshots) {
        setSnapshots(response.data.snapshots);
      }
    } catch (error) {
      console.error("Failed to fetch snapshots:", error);
    } finally {
      setLoading(false);
    }
  };

  const getConnectionStatus = (snapshot) => {
    if (!snapshot.timestamp) return "offline";
    
    const lastUpdate = new Date(snapshot.timestamp);
    const now = new Date();
    const diffSeconds = (now - lastUpdate) / 1000;
    
    if (diffSeconds < 30) return "online";
    if (diffSeconds < 120) return "degraded";
    return "offline";
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return "Never";
    const date = new Date(timestamp);
    return date.toLocaleTimeString();
  };

  const formatTimeDiff = (timestamp) => {
    if (!timestamp) return "N/A";
    
    const lastUpdate = new Date(timestamp);
    const now = new Date();
    const diffSeconds = Math.floor((now - lastUpdate) / 1000);
    
    if (diffSeconds < 5) return "Just now";
    if (diffSeconds < 60) return `${diffSeconds}s ago`;
    if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
    return `${Math.floor(diffSeconds / 3600)}h ago`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="live-cameras-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            LIVE CAMERAS
          </h1>
          <p className="text-muted-foreground mt-1">
            Real-time camera feeds from edge devices
          </p>
        </div>
        
        <div className="flex items-center gap-4">
          {/* Auto Refresh Toggle */}
          <div className="flex items-center gap-2">
            <Button
              variant={autoRefresh ? "default" : "outline"}
              size="sm"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={autoRefresh ? "bg-emerald-600 hover:bg-emerald-700" : ""}
            >
              {autoRefresh ? (
                <><Zap className="w-4 h-4 mr-2" /> Live</>
              ) : (
                <><Eye className="w-4 h-4 mr-2" /> Paused</>
              )}
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              onClick={fetchSnapshots}
              disabled={loading}
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </div>

      {/* No Cameras Message */}
      {snapshots.length === 0 && (
        <Card className="bg-card/50 border-white/5">
          <CardContent className="py-16 text-center">
            <Camera className="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-30" />
            <h3 className="text-xl font-semibold mb-2">No Camera Feeds Available</h3>
            <p className="text-muted-foreground max-w-md mx-auto">
              Camera feeds will appear here once your edge device is running and connected to your RTSP cameras.
            </p>
            <div className="mt-6 p-4 bg-secondary/50 rounded-lg max-w-lg mx-auto text-left">
              <h4 className="font-medium mb-2">Setup Checklist:</h4>
              <ul className="text-sm text-muted-foreground space-y-1">
                <li>1. Add cameras with RTSP URLs in Admin → Cameras</li>
                <li>2. Provision an edge device in Admin → Edge Devices</li>
                <li>3. Install and run the edge processor at your location</li>
                <li>4. Camera feeds will appear automatically</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Camera Grid */}
      {snapshots.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {snapshots.map((snapshot) => {
            const status = getConnectionStatus(snapshot);
            const colors = statusColors[status];
            const health = snapshot.health || {};
            
            return (
              <Card 
                key={snapshot.camera_id}
                className={`bg-card/50 border-white/5 overflow-hidden cursor-pointer transition-all hover:border-cyan-500/50 ${
                  selectedCamera === snapshot.camera_id ? 'ring-2 ring-cyan-500' : ''
                }`}
                onClick={() => setSelectedCamera(selectedCamera === snapshot.camera_id ? null : snapshot.camera_id)}
              >
                {/* Camera Feed */}
                <div className="relative aspect-video bg-black">
                  {snapshot.image ? (
                    <img 
                      src={`data:image/jpeg;base64,${snapshot.image}`}
                      alt={snapshot.camera_name}
                      className="w-full h-full object-contain"
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full">
                      <Camera className="w-12 h-12 text-muted-foreground opacity-30" />
                    </div>
                  )}
                  
                  {/* Status Overlay */}
                  <div className="absolute top-2 left-2 flex items-center gap-2">
                    <div className={`flex items-center gap-1.5 px-2 py-1 rounded-full ${colors.bg} backdrop-blur-sm`}>
                      <div className={`w-2 h-2 rounded-full ${colors.dot} ${status === 'online' ? 'animate-pulse' : ''}`} />
                      <span className={`text-xs font-medium ${colors.text} uppercase`}>{status}</span>
                    </div>
                  </div>
                  
                  {/* Timestamp Overlay */}
                  <div className="absolute bottom-2 left-2 px-2 py-1 rounded bg-black/70 backdrop-blur-sm">
                    <span className="text-xs text-white/80">{formatTimeDiff(snapshot.timestamp)}</span>
                  </div>
                  
                  {/* FPS Overlay */}
                  {health.fps > 0 && (
                    <div className="absolute bottom-2 right-2 px-2 py-1 rounded bg-black/70 backdrop-blur-sm">
                      <span className="text-xs text-cyan-400 font-mono">{health.fps} FPS</span>
                    </div>
                  )}
                  
                  {/* Fullscreen Button */}
                  <Button
                    variant="ghost"
                    size="sm"
                    className="absolute top-2 right-2 bg-black/50 hover:bg-black/70"
                    onClick={(e) => {
                      e.stopPropagation();
                      // TODO: Open fullscreen modal
                    }}
                  >
                    <Maximize2 className="w-4 h-4" />
                  </Button>
                </div>
                
                {/* Camera Info */}
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold">{snapshot.camera_name || 'Unknown Camera'}</h3>
                    {status === 'online' && health.frames_received > 0 && (
                      <Badge variant="outline" className="text-xs">
                        {health.frames_received} frames
                      </Badge>
                    )}
                  </div>
                  
                  {/* Health Metrics (expanded view) */}
                  {selectedCamera === snapshot.camera_id && health && (
                    <div className="mt-3 pt-3 border-t border-white/5 space-y-2 text-sm">
                      <div className="grid grid-cols-2 gap-2">
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">Frames Received:</span>
                          <span className="font-mono">{health.frames_received || 0}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">Frames Dropped:</span>
                          <span className={`font-mono ${health.frames_dropped > 10 ? 'text-amber-400' : ''}`}>
                            {health.frames_dropped || 0}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">Decode Errors:</span>
                          <span className={`font-mono ${health.decode_errors > 50 ? 'text-red-400' : ''}`}>
                            {health.decode_errors || 0}
                          </span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-muted-foreground">Reconnects:</span>
                          <span className={`font-mono ${health.reconnect_count > 5 ? 'text-amber-400' : ''}`}>
                            {health.reconnect_count || 0}
                          </span>
                        </div>
                      </div>
                      
                      {health.decode_errors > 50 && (
                        <div className="flex items-center gap-2 p-2 rounded bg-amber-500/10 text-amber-400 text-xs">
                          <AlertTriangle className="w-4 h-4" />
                          High decode errors - check network connection
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center justify-center gap-6 text-sm text-muted-foreground">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500" />
          <span>Online ({"<"}30s)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-amber-500" />
          <span>Degraded (30s-2m)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-red-500" />
          <span>Offline ({">"}2m)</span>
        </div>
      </div>
    </div>
  );
}
