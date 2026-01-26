import { useState, useEffect } from "react";
import axios from "axios";
import { 
  Cpu, 
  Building2,
  Eye,
  Save,
  RefreshCw,
  Zap,
  Brain,
  Scan,
  MessageSquare,
  AlertTriangle,
  CheckCircle
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Switch } from "../../components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { Label } from "../../components/ui/label";
import { Slider } from "../../components/ui/slider";
import { toast } from "sonner";
import { motion } from "framer-motion";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AdminAIControl() {
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [mlStatus, setMlStatus] = useState(null);

  useEffect(() => {
    fetchClients();
    fetchMLStatus();
  }, []);

  useEffect(() => {
    if (selectedClient) {
      fetchClientSettings(selectedClient);
    }
  }, [selectedClient]);

  const fetchClients = async () => {
    try {
      const response = await axios.get(`${API}/admin/clients?limit=100`, { withCredentials: true });
      setClients(response.data.clients || []);
      if (response.data.clients?.length > 0) {
        setSelectedClient(response.data.clients[0].client_id);
      }
    } catch (error) {
      console.error("Failed to fetch clients:", error);
      toast.error("Failed to load clients");
    } finally {
      setLoading(false);
    }
  };

  const fetchMLStatus = async () => {
    try {
      const response = await axios.get(`${API}/ml/status`, { withCredentials: true });
      setMlStatus(response.data);
    } catch (error) {
      console.error("Failed to fetch ML status:", error);
    }
  };

  const fetchClientSettings = async (clientId) => {
    try {
      const response = await axios.get(`${API}/admin/ai/settings/${clientId}`, { withCredentials: true });
      setSettings(response.data.settings);
    } catch (error) {
      console.error("Failed to fetch AI settings:", error);
      // Set defaults if no settings exist
      setSettings({
        enable_yolo: true,
        enable_deepface: true,
        enable_pose: true,
        enable_gpt_analysis: true,
        detection_sensitivity: "medium",
        threat_threshold: 0.6
      });
    }
  };

  const handleSaveSettings = async () => {
    if (!selectedClient || !settings) return;
    
    setSaving(true);
    try {
      await axios.put(`${API}/admin/ai/settings`, {
        client_id: selectedClient,
        ...settings
      }, { withCredentials: true });
      
      toast.success("AI settings saved successfully");
    } catch (error) {
      toast.error("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const getClientName = (clientId) => {
    const client = clients.find(c => c.client_id === clientId);
    return client?.name || "Unknown";
  };

  const models = [
    {
      key: "enable_yolo",
      name: "YOLO v8",
      description: "Real-time person detection and tracking",
      icon: Eye,
      color: "purple",
      status: mlStatus?.yolo?.loaded ? "active" : "inactive"
    },
    {
      key: "enable_pose",
      name: "Pose Estimation",
      description: "Body posture and movement analysis",
      icon: Scan,
      color: "pink",
      status: mlStatus?.yolo_pose?.loaded ? "active" : "inactive"
    },
    {
      key: "enable_deepface",
      name: "DeepFace",
      description: "Facial recognition for watchlist matching",
      icon: Brain,
      color: "blue",
      status: mlStatus?.deepface?.initialized ? "active" : "inactive"
    },
    {
      key: "enable_gpt_analysis",
      name: "GPT-5.2 Vision",
      description: "Advanced behavior analysis and scene understanding",
      icon: MessageSquare,
      color: "cyan",
      status: mlStatus?.gpt_vision?.available ? "active" : "inactive"
    }
  ];

  const colorClasses = {
    purple: { bg: "bg-purple-500/10", border: "border-purple-500/30", text: "text-purple-400" },
    pink: { bg: "bg-pink-500/10", border: "border-pink-500/30", text: "text-pink-400" },
    blue: { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400" },
    cyan: { bg: "bg-cyan-500/10", border: "border-cyan-500/30", text: "text-cyan-400" }
  };

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <div className="skeleton h-8 w-48 mb-4" />
        <div className="grid grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="skeleton h-32 rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="admin-ai-control-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            AI MODEL CONTROL
          </h1>
          <p className="text-muted-foreground mt-1">
            Configure AI detection models and sensitivity per client
          </p>
        </div>
        <Button
          onClick={handleSaveSettings}
          disabled={saving || !selectedClient}
          className="flex items-center gap-2"
        >
          {saving ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Save Settings
        </Button>
      </div>

      {/* Client Selector */}
      <Card className="bg-card/50 border-white/5">
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <Building2 className="w-5 h-5 text-muted-foreground" />
            <div className="flex-1">
              <Label className="text-xs text-muted-foreground uppercase tracking-wider">
                Select Client
              </Label>
              <Select value={selectedClient || ""} onValueChange={setSelectedClient}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select a client to configure" />
                </SelectTrigger>
                <SelectContent>
                  {clients.map(client => (
                    <SelectItem key={client.client_id} value={client.client_id}>
                      {client.name} ({client.subscription?.plan || 'trial'})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {selectedClient && settings && (
        <>
          {/* ML Models */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {models.map((model, idx) => {
              const colors = colorClasses[model.color];
              const ModelIcon = model.icon;
              const enabled = settings[model.key];
              
              return (
                <motion.div
                  key={model.key}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: idx * 0.1 }}
                >
                  <Card className={`bg-card/50 border-white/5 ${enabled ? '' : 'opacity-60'}`}>
                    <CardContent className="p-6">
                      <div className="flex items-start justify-between mb-4">
                        <div className="flex items-center gap-3">
                          <div className={`p-3 rounded-md ${colors.bg} border ${colors.border}`}>
                            <ModelIcon className={`w-6 h-6 ${colors.text}`} />
                          </div>
                          <div>
                            <h3 className="font-semibold">{model.name}</h3>
                            <p className="text-xs text-muted-foreground">{model.description}</p>
                          </div>
                        </div>
                        <Switch
                          checked={enabled}
                          onCheckedChange={(checked) => setSettings({ ...settings, [model.key]: checked })}
                        />
                      </div>
                      <div className="flex items-center justify-between">
                        <Badge 
                          variant="outline"
                          className={model.status === "active" 
                            ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/30"
                            : "bg-gray-500/10 text-gray-500 border-gray-500/30"
                          }
                        >
                          {model.status === "active" ? (
                            <>
                              <CheckCircle className="w-3 h-3 mr-1" />
                              Active
                            </>
                          ) : (
                            <>
                              <AlertTriangle className="w-3 h-3 mr-1" />
                              Inactive
                            </>
                          )}
                        </Badge>
                        <span className={`text-xs ${enabled ? colors.text : 'text-muted-foreground'}`}>
                          {enabled ? 'Enabled' : 'Disabled'} for {getClientName(selectedClient)}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              );
            })}
          </div>

          {/* Detection Settings */}
          <Card className="bg-card/50 border-white/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-amber-500" />
                Detection Settings
              </CardTitle>
              <CardDescription>
                Fine-tune detection sensitivity and thresholds for {getClientName(selectedClient)}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <Label>Detection Sensitivity</Label>
                <Select
                  value={settings.detection_sensitivity}
                  onValueChange={(value) => setSettings({ ...settings, detection_sensitivity: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-emerald-500" />
                        Low - Fewer alerts, higher confidence required
                      </div>
                    </SelectItem>
                    <SelectItem value="medium">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-amber-500" />
                        Medium - Balanced detection
                      </div>
                    </SelectItem>
                    <SelectItem value="high">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-red-500" />
                        High - More alerts, lower threshold
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label>Threat Threshold</Label>
                  <span className="text-sm font-mono text-muted-foreground">
                    {(settings.threat_threshold * 100).toFixed(0)}%
                  </span>
                </div>
                <Slider
                  value={[settings.threat_threshold * 100]}
                  onValueChange={([value]) => setSettings({ ...settings, threat_threshold: value / 100 })}
                  max={100}
                  min={20}
                  step={5}
                  className="w-full"
                />
                <p className="text-xs text-muted-foreground">
                  Incidents with confidence below this threshold will not trigger alerts
                </p>
              </div>
            </CardContent>
          </Card>

          {/* System-wide ML Status */}
          <Card className="bg-card/50 border-white/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Cpu className="w-5 h-5 text-cyan-500" />
                System ML Status
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {mlStatus && Object.entries(mlStatus).map(([key, value]) => {
                  if (typeof value !== 'object') return null;
                  const isActive = value.loaded || value.initialized || value.available || value.active;
                  return (
                    <div 
                      key={key}
                      className={`p-3 rounded-lg border ${isActive 
                        ? 'bg-emerald-500/10 border-emerald-500/30' 
                        : 'bg-gray-500/10 border-gray-500/30'
                      }`}
                    >
                      <p className="text-xs text-muted-foreground uppercase">{key.replace('_', ' ')}</p>
                      <p className={`text-sm font-medium ${isActive ? 'text-emerald-400' : 'text-gray-400'}`}>
                        {isActive ? 'Active' : 'Inactive'}
                      </p>
                      {value.model && (
                        <p className="text-xs text-muted-foreground">{value.model}</p>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
