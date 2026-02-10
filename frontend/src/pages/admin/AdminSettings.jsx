import { useState, useEffect } from "react";
import axios from "axios";
import { 
  Settings, 
  User, 
  Shield, 
  Bell, 
  Database,
  Key,
  Globe,
  Save,
  RefreshCw,
  Check,
  AlertTriangle
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Switch } from "../../components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { toast } from "sonner";
import { useAuth } from "../../context/AuthContext";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const getAuthHeaders = () => {
  const token = localStorage.getItem("session_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export default function AdminSettings() {
  const { user } = useAuth();
  const [saving, setSaving] = useState(false);
  const [systemHealth, setSystemHealth] = useState(null);
  
  // Profile settings
  const [profile, setProfile] = useState({
    name: user?.name || "",
    email: user?.email || ""
  });
  
  // System settings
  const [systemSettings, setSystemSettings] = useState({
    maintenanceMode: false,
    allowNewRegistrations: true,
    requireEmailVerification: false,
    sessionTimeoutDays: 7,
    maxLoginAttempts: 5
  });
  
  // Notification settings
  const [notifications, setNotifications] = useState({
    emailOnCriticalIncident: true,
    emailOnNewClient: true,
    emailOnDeviceOffline: true,
    dailySummaryEmail: false
  });

  useEffect(() => {
    fetchSystemHealth();
    fetchSystemSettings();
    fetchNotificationSettings();
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

  const fetchSystemSettings = async () => {
    try {
      const response = await axios.get(`${API}/admin/system/settings`, {
        withCredentials: true,
        headers: getAuthHeaders()
      });
      if (response.data) {
        setSystemSettings({
          maintenanceMode: response.data.maintenance_mode ?? false,
          allowNewRegistrations: response.data.allow_new_registrations ?? true,
          requireEmailVerification: response.data.require_email_verification ?? false,
          sessionTimeoutDays: response.data.session_timeout_days ?? 7,
          maxLoginAttempts: response.data.max_login_attempts ?? 5
        });
      }
    } catch (error) {
      console.error("Failed to fetch system settings:", error);
    }
  };

  const fetchNotificationSettings = async () => {
    try {
      const response = await axios.get(`${API}/admin/notifications/settings`, {
        withCredentials: true,
        headers: getAuthHeaders()
      });
      if (response.data) {
        setNotifications({
          emailOnCriticalIncident: response.data.email_on_critical_incident ?? true,
          emailOnNewClient: response.data.email_on_new_client ?? true,
          emailOnDeviceOffline: response.data.email_on_device_offline ?? true,
          dailySummaryEmail: response.data.daily_summary_email ?? false
        });
      }
    } catch (error) {
      console.error("Failed to fetch notification settings:", error);
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

  const handleSaveSystem = async () => {
    setSaving(true);
    try {
      const response = await axios.put(`${API}/admin/system/settings`, {
        maintenance_mode: systemSettings.maintenanceMode,
        allow_new_registrations: systemSettings.allowNewRegistrations,
        require_email_verification: systemSettings.requireEmailVerification,
        session_timeout_days: systemSettings.sessionTimeoutDays,
        max_login_attempts: systemSettings.maxLoginAttempts
      }, {
        withCredentials: true,
        headers: getAuthHeaders()
      });
      
      if (response.data.success) {
        toast.success("System settings updated");
      } else {
        toast.error(response.data.message || "Failed to update system settings");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update system settings");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveNotifications = async () => {
    setSaving(true);
    try {
      const response = await axios.put(`${API}/admin/notifications/settings`, {
        email_on_critical_incident: notifications.emailOnCriticalIncident,
        email_on_new_client: notifications.emailOnNewClient,
        email_on_device_offline: notifications.emailOnDeviceOffline,
        daily_summary_email: notifications.dailySummaryEmail
      }, {
        withCredentials: true,
        headers: getAuthHeaders()
      });
      
      if (response.data.success) {
        toast.success("Notification settings updated");
      } else {
        toast.error(response.data.message || "Failed to update notification settings");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to update notification settings");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-6" data-testid="admin-settings">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
          SETTINGS
        </h1>
        <p className="text-muted-foreground mt-1">
          Manage your account and system preferences
        </p>
      </div>

      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList className="bg-card/50 border border-white/10">
          <TabsTrigger value="profile" className="data-[state=active]:bg-white/10">
            <User className="w-4 h-4 mr-2" />
            Profile
          </TabsTrigger>
          <TabsTrigger value="system" className="data-[state=active]:bg-white/10">
            <Shield className="w-4 h-4 mr-2" />
            System
          </TabsTrigger>
          <TabsTrigger value="notifications" className="data-[state=active]:bg-white/10">
            <Bell className="w-4 h-4 mr-2" />
            Notifications
          </TabsTrigger>
          <TabsTrigger value="status" className="data-[state=active]:bg-white/10">
            <Database className="w-4 h-4 mr-2" />
            Status
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
              <CardDescription>Update your account details</CardDescription>
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
                    onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                    placeholder="Your email"
                    disabled
                  />
                  <p className="text-xs text-muted-foreground">Email cannot be changed</p>
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Role</Label>
                <div className="flex items-center gap-2">
                  <span className="px-3 py-1 rounded bg-red-500/20 text-red-400 border border-red-500/30 text-sm">
                    Super Admin
                  </span>
                  <span className="text-sm text-muted-foreground">Full system access</span>
                </div>
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

        {/* System Tab */}
        <TabsContent value="system">
          <Card className="bg-card/50 border-white/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="w-5 h-5 text-purple-500" />
                System Settings
              </CardTitle>
              <CardDescription>Configure system-wide preferences</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5">
                  <div>
                    <p className="font-medium">Maintenance Mode</p>
                    <p className="text-sm text-muted-foreground">Disable access for non-admin users</p>
                  </div>
                  <Switch
                    checked={systemSettings.maintenanceMode}
                    onCheckedChange={(checked) => setSystemSettings({ ...systemSettings, maintenanceMode: checked })}
                  />
                </div>
                
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5">
                  <div>
                    <p className="font-medium">Allow New Registrations</p>
                    <p className="text-sm text-muted-foreground">Allow new users to create accounts</p>
                  </div>
                  <Switch
                    checked={systemSettings.allowNewRegistrations}
                    onCheckedChange={(checked) => setSystemSettings({ ...systemSettings, allowNewRegistrations: checked })}
                  />
                </div>
                
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5">
                  <div>
                    <p className="font-medium">Require Email Verification</p>
                    <p className="text-sm text-muted-foreground">Users must verify email before access</p>
                  </div>
                  <Switch
                    checked={systemSettings.requireEmailVerification}
                    onCheckedChange={(checked) => setSystemSettings({ ...systemSettings, requireEmailVerification: checked })}
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>Session Timeout (days)</Label>
                    <Input
                      type="number"
                      value={systemSettings.sessionTimeoutDays}
                      onChange={(e) => setSystemSettings({ ...systemSettings, sessionTimeoutDays: parseInt(e.target.value) })}
                      min={1}
                      max={30}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label>Max Login Attempts</Label>
                    <Input
                      type="number"
                      value={systemSettings.maxLoginAttempts}
                      onChange={(e) => setSystemSettings({ ...systemSettings, maxLoginAttempts: parseInt(e.target.value) })}
                      min={3}
                      max={10}
                    />
                  </div>
                </div>
              </div>

              <div className="pt-4 border-t border-white/5">
                <Button onClick={handleSaveSystem} disabled={saving}>
                  {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                  Save System Settings
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Notifications Tab */}
        <TabsContent value="notifications">
          <Card className="bg-card/50 border-white/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="w-5 h-5 text-amber-500" />
                Notification Preferences
              </CardTitle>
              <CardDescription>Configure email and alert notifications</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5">
                  <div>
                    <p className="font-medium">Critical Incident Alerts</p>
                    <p className="text-sm text-muted-foreground">Email on critical incidents across all clients</p>
                  </div>
                  <Switch
                    checked={notifications.emailOnCriticalIncident}
                    onCheckedChange={(checked) => setNotifications({ ...notifications, emailOnCriticalIncident: checked })}
                  />
                </div>
                
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5">
                  <div>
                    <p className="font-medium">New Client Registration</p>
                    <p className="text-sm text-muted-foreground">Email when a new client signs up</p>
                  </div>
                  <Switch
                    checked={notifications.emailOnNewClient}
                    onCheckedChange={(checked) => setNotifications({ ...notifications, emailOnNewClient: checked })}
                  />
                </div>
                
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5">
                  <div>
                    <p className="font-medium">Device Offline Alerts</p>
                    <p className="text-sm text-muted-foreground">Email when an edge device goes offline</p>
                  </div>
                  <Switch
                    checked={notifications.emailOnDeviceOffline}
                    onCheckedChange={(checked) => setNotifications({ ...notifications, emailOnDeviceOffline: checked })}
                  />
                </div>
                
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5">
                  <div>
                    <p className="font-medium">Daily Summary</p>
                    <p className="text-sm text-muted-foreground">Receive daily summary of all incidents</p>
                  </div>
                  <Switch
                    checked={notifications.dailySummaryEmail}
                    onCheckedChange={(checked) => setNotifications({ ...notifications, dailySummaryEmail: checked })}
                  />
                </div>
              </div>

              <div className="pt-4 border-t border-white/5">
                <Button onClick={handleSaveNotifications} disabled={saving}>
                  {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                  Save Notification Settings
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Status Tab */}
        <TabsContent value="status">
          <div className="grid gap-6">
            <Card className="bg-card/50 border-white/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="w-5 h-5 text-cyan-500" />
                  System Status
                </CardTitle>
                <CardDescription>Current system health and metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div className="p-4 rounded-lg bg-white/[0.02] border border-white/5">
                    <div className="flex items-center gap-2 mb-2">
                      {systemHealth?.status === "operational" ? (
                        <Check className="w-4 h-4 text-emerald-500" />
                      ) : (
                        <AlertTriangle className="w-4 h-4 text-amber-500" />
                      )}
                      <span className="text-sm text-muted-foreground">Status</span>
                    </div>
                    <p className="font-semibold capitalize">{systemHealth?.status || "Loading..."}</p>
                  </div>
                  
                  <div className="p-4 rounded-lg bg-white/[0.02] border border-white/5">
                    <div className="flex items-center gap-2 mb-2">
                      <Database className="w-4 h-4 text-blue-500" />
                      <span className="text-sm text-muted-foreground">Database</span>
                    </div>
                    <p className="font-semibold capitalize">{systemHealth?.database || "Loading..."}</p>
                  </div>
                  
                  <div className="p-4 rounded-lg bg-white/[0.02] border border-white/5">
                    <div className="flex items-center gap-2 mb-2">
                      <Globe className="w-4 h-4 text-purple-500" />
                      <span className="text-sm text-muted-foreground">Active Streams</span>
                    </div>
                    <p className="font-semibold">{systemHealth?.active_streams || 0}</p>
                  </div>
                  
                  <div className="p-4 rounded-lg bg-white/[0.02] border border-white/5">
                    <div className="flex items-center gap-2 mb-2">
                      <Key className="w-4 h-4 text-amber-500" />
                      <span className="text-sm text-muted-foreground">Queue Depth</span>
                    </div>
                    <p className="font-semibold">{systemHealth?.queue_depth || 0}</p>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-white/5">
                  <Button variant="outline" onClick={fetchSystemHealth}>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Refresh Status
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-card/50 border-white/5">
              <CardHeader>
                <CardTitle>System Information</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between py-2 border-b border-white/5">
                    <span className="text-muted-foreground">Version</span>
                    <span className="font-mono">2.0.0</span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-white/5">
                    <span className="text-muted-foreground">Environment</span>
                    <span className="font-mono">Production</span>
                  </div>
                  <div className="flex justify-between py-2 border-b border-white/5">
                    <span className="text-muted-foreground">API Endpoint</span>
                    <span className="font-mono text-xs">{API}</span>
                  </div>
                  <div className="flex justify-between py-2">
                    <span className="text-muted-foreground">Last Updated</span>
                    <span className="font-mono">{systemHealth?.timestamp ? new Date(systemHealth.timestamp).toLocaleString() : "-"}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
