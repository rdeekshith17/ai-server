import { useState, useEffect } from "react";
import axios from "axios";
import { 
  Settings, 
  User, 
  Bell, 
  Shield,
  Camera,
  Save,
  RefreshCw,
  Smartphone
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Switch } from "../components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const getAuthHeaders = () => {
  const token = localStorage.getItem("session_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export default function ClientSettings() {
  const { user } = useAuth();
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  
  // Profile settings
  const [profile, setProfile] = useState({
    name: user?.name || "",
    email: user?.email || ""
  });
  
  // Detection settings
  const [detection, setDetection] = useState({
    sensitivity: "medium",
    enablePoseDetection: true,
    enableFaceRecognition: true,
    enableGptAnalysis: true,
    confidenceThreshold: 0.6
  });
  
  // Alert settings
  const [alerts, setAlerts] = useState({
    alertOnCritical: true,
    alertOnWarning: false,
    emailAlerts: true,
    whatsappAlerts: false,
    whatsappNumber: ""
  });

  useEffect(() => {
    if (user?.client_id) {
      fetchSettings();
    } else {
      setLoading(false);
    }
  }, [user?.client_id]);

  const fetchSettings = async () => {
    try {
      const response = await axios.get(`${API}/dashboard/stats?client_id=${user.client_id}`, {
        withCredentials: true,
        headers: getAuthHeaders()
      });
      
      if (response.data.settings) {
        const settings = response.data.settings;
        setAlerts({
          alertOnCritical: settings.alert_on_critical ?? true,
          alertOnWarning: settings.alert_on_warning ?? false,
          emailAlerts: settings.alert_email ?? true,
          whatsappAlerts: settings.whatsapp_numbers?.length > 0,
          whatsappNumber: settings.whatsapp_numbers?.[0] || ""
        });
        setDetection({
          ...detection,
          sensitivity: settings.detection_sensitivity || "medium"
        });
      }
    } catch (error) {
      console.error("Failed to fetch settings:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      const response = await axios.put(`${API}/users/${user.user_id}/profile`, {
        name: profile.name
      }, {
        withCredentials: true,
        headers: getAuthHeaders()
      });
      
      if (response.data.success) {
        toast.success("Profile updated successfully");
      } else {
        toast.error(response.data.message || "Failed to update profile");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveDetection = async () => {
    if (!user?.client_id) {
      toast.error("No client associated with your account");
      return;
    }
    
    setSaving(true);
    try {
      const response = await axios.put(`${API}/client/detection-settings/${user.client_id}`, {
        sensitivity: detection.sensitivity,
        enable_pose_detection: detection.enablePoseDetection,
        enable_face_recognition: detection.enableFaceRecognition,
        enable_gpt_analysis: detection.enableGptAnalysis,
        confidence_threshold: detection.confidenceThreshold
      }, {
        withCredentials: true,
        headers: getAuthHeaders()
      });
      
      if (response.data.success) {
        toast.success("Detection settings updated");
      } else {
        toast.error(response.data.message || "Failed to update detection settings");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update detection settings");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveAlerts = async () => {
    if (!user?.client_id) {
      toast.error("No client associated with your account");
      return;
    }
    
    setSaving(true);
    try {
      const payload = {
        alert_on_critical: alerts.alertOnCritical,
        alert_on_warning: alerts.alertOnWarning,
        alert_email: alerts.emailAlerts
      };
      
      // Add WhatsApp number if enabled
      if (alerts.whatsappAlerts && alerts.whatsappNumber) {
        payload.whatsapp_numbers = [alerts.whatsappNumber];
      } else {
        payload.whatsapp_numbers = [];
      }
      
      const response = await axios.put(`${API}/alerts/settings/${user.client_id}`, payload, {
        withCredentials: true,
        headers: getAuthHeaders()
      });
      
      if (response.data.success) {
        toast.success("Alert settings updated");
      } else {
        toast.error(response.data.message || "Failed to update alert settings");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update alert settings");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <div className="skeleton h-8 w-48" />
        <div className="skeleton h-64 w-full rounded-lg" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="client-settings">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
          SETTINGS
        </h1>
        <p className="text-muted-foreground mt-1">
          Manage your account and detection preferences
        </p>
      </div>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList className="bg-card/50 border border-white/10">
          <TabsTrigger value="profile" className="data-[state=active]:bg-white/10">
            <User className="w-4 h-4 mr-2" />
            Profile
          </TabsTrigger>
          <TabsTrigger value="detection" className="data-[state=active]:bg-white/10">
            <Camera className="w-4 h-4 mr-2" />
            Detection
          </TabsTrigger>
          <TabsTrigger value="alerts" className="data-[state=active]:bg-white/10">
            <Bell className="w-4 h-4 mr-2" />
            Alerts
          </TabsTrigger>
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="profile">
          <Card className="bg-card/50 border-white/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <User className="w-5 h-5 text-blue-500" />
                Profile Information
              </CardTitle>
              <CardDescription>Your account details</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label>Full Name</Label>
                  <Input
                    value={profile.name}
                    onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                    placeholder="Your name"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input
                    value={profile.email}
                    disabled
                  />
                  <p className="text-xs text-muted-foreground">Email cannot be changed</p>
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-2">
                  <Label>Role</Label>
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-sm capitalize">
                      {user?.role?.replace("_", " ") || "User"}
                    </span>
                  </div>
                </div>
                {user?.client_name && (
                  <div className="space-y-2">
                    <Label>Organization</Label>
                    <p className="text-sm font-medium">{user.client_name}</p>
                  </div>
                )}
              </div>

              <div className="pt-4 border-t border-white/5">
                <Button onClick={handleSaveProfile} disabled={saving}>
                  {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                  Save Profile
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Detection Tab */}
        <TabsContent value="detection">
          <Card className="bg-card/50 border-white/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Camera className="w-5 h-5 text-purple-500" />
                Detection Settings
              </CardTitle>
              <CardDescription>Configure AI detection parameters</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label>Detection Sensitivity</Label>
                <Select
                  value={detection.sensitivity}
                  onValueChange={(value) => setDetection({ ...detection, sensitivity: value })}
                >
                  <SelectTrigger className="w-full max-w-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low - Fewer alerts, higher precision</SelectItem>
                    <SelectItem value="medium">Medium - Balanced</SelectItem>
                    <SelectItem value="high">High - More alerts, higher recall</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5">
                  <div>
                    <p className="font-medium">Pose Detection</p>
                    <p className="text-sm text-muted-foreground">Detect suspicious body movements</p>
                  </div>
                  <Switch
                    checked={detection.enablePoseDetection}
                    onCheckedChange={(checked) => setDetection({ ...detection, enablePoseDetection: checked })}
                  />
                </div>
                
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5">
                  <div>
                    <p className="font-medium">Face Recognition</p>
                    <p className="text-sm text-muted-foreground">Match faces against watchlist</p>
                  </div>
                  <Switch
                    checked={detection.enableFaceRecognition}
                    onCheckedChange={(checked) => setDetection({ ...detection, enableFaceRecognition: checked })}
                  />
                </div>
                
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5">
                  <div>
                    <p className="font-medium">AI Behavior Analysis</p>
                    <p className="text-sm text-muted-foreground">Use GPT Vision for detailed analysis</p>
                  </div>
                  <Switch
                    checked={detection.enableGptAnalysis}
                    onCheckedChange={(checked) => setDetection({ ...detection, enableGptAnalysis: checked })}
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>Confidence Threshold ({(detection.confidenceThreshold * 100).toFixed(0)}%)</Label>
                <input
                  type="range"
                  min="0.3"
                  max="0.9"
                  step="0.05"
                  value={detection.confidenceThreshold}
                  onChange={(e) => setDetection({ ...detection, confidenceThreshold: parseFloat(e.target.value) })}
                  className="w-full max-w-xs"
                />
                <p className="text-xs text-muted-foreground">
                  Higher threshold = fewer false positives, lower threshold = catch more incidents
                </p>
              </div>

              <div className="pt-4 border-t border-white/5">
                <Button onClick={handleSaveDetection} disabled={saving}>
                  {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                  Save Detection Settings
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Alerts Tab */}
        <TabsContent value="alerts">
          <Card className="bg-card/50 border-white/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="w-5 h-5 text-amber-500" />
                Alert Preferences
              </CardTitle>
              <CardDescription>Configure how you receive incident alerts</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5">
                  <div>
                    <p className="font-medium">Critical Incident Alerts</p>
                    <p className="text-sm text-muted-foreground">Get notified for critical threats</p>
                  </div>
                  <Switch
                    checked={alerts.alertOnCritical}
                    onCheckedChange={(checked) => setAlerts({ ...alerts, alertOnCritical: checked })}
                  />
                </div>
                
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5">
                  <div>
                    <p className="font-medium">Warning Alerts</p>
                    <p className="text-sm text-muted-foreground">Get notified for warning-level incidents</p>
                  </div>
                  <Switch
                    checked={alerts.alertOnWarning}
                    onCheckedChange={(checked) => setAlerts({ ...alerts, alertOnWarning: checked })}
                  />
                </div>
                
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5">
                  <div>
                    <p className="font-medium">Email Alerts</p>
                    <p className="text-sm text-muted-foreground">Receive alerts via email</p>
                  </div>
                  <Switch
                    checked={alerts.emailAlerts}
                    onCheckedChange={(checked) => setAlerts({ ...alerts, emailAlerts: checked })}
                  />
                </div>
                
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5">
                  <div>
                    <p className="font-medium">WhatsApp Alerts</p>
                    <p className="text-sm text-muted-foreground">Receive alerts via WhatsApp</p>
                  </div>
                  <Switch
                    checked={alerts.whatsappAlerts}
                    onCheckedChange={(checked) => setAlerts({ ...alerts, whatsappAlerts: checked })}
                  />
                </div>
              </div>

              {alerts.whatsappAlerts && (
                <div className="space-y-2 p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/30">
                  <Label className="flex items-center gap-2">
                    <Smartphone className="w-4 h-4 text-emerald-500" />
                    WhatsApp Number
                  </Label>
                  <Input
                    placeholder="+1 555-0123"
                    value={alerts.whatsappNumber}
                    onChange={(e) => setAlerts({ ...alerts, whatsappNumber: e.target.value })}
                    className="max-w-xs"
                  />
                  <p className="text-xs text-muted-foreground">Include country code (e.g., +91 for India)</p>
                </div>
              )}

              <div className="pt-4 border-t border-white/5">
                <Button onClick={handleSaveAlerts} disabled={saving}>
                  {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                  Save Alert Settings
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
