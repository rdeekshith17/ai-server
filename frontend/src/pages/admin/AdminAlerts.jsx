import { useState, useEffect } from "react";
import axios from "axios";
import { 
  Bell, 
  Building2,
  Save,
  RefreshCw,
  MessageSquare,
  Mail,
  Plus,
  Trash2,
  Send,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Shield
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
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
import { ScrollArea } from "../../components/ui/scroll-area";
import { toast } from "sonner";
import { motion } from "framer-motion";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AdminAlerts() {
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [settings, setSettings] = useState(null);
  const [alertLog, setAlertLog] = useState([]);
  const [serviceStatus, setServiceStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testNumber, setTestNumber] = useState("");
  const [sendingTest, setSendingTest] = useState(false);
  const [newWhatsAppNumber, setNewWhatsAppNumber] = useState("");

  useEffect(() => {
    fetchClients();
    fetchServiceStatus();
  }, []);

  useEffect(() => {
    if (selectedClient) {
      fetchClientSettings(selectedClient);
      fetchAlertLog(selectedClient);
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

  const fetchServiceStatus = async () => {
    try {
      const response = await axios.get(`${API}/alerts/status`, { withCredentials: true });
      setServiceStatus(response.data);
    } catch (error) {
      console.error("Failed to fetch service status:", error);
    }
  };

  const fetchClientSettings = async (clientId) => {
    try {
      const response = await axios.get(`${API}/alerts/settings/${clientId}`, { withCredentials: true });
      setSettings(response.data.settings || {
        enabled: false,
        alert_on_critical: true,
        alert_on_warning: false,
        whatsapp_numbers: [],
        email_addresses: [],
        quiet_hours_start: null,
        quiet_hours_end: null,
        cooldown_minutes: 5
      });
    } catch (error) {
      console.error("Failed to fetch alert settings:", error);
      setSettings({
        enabled: false,
        alert_on_critical: true,
        alert_on_warning: false,
        whatsapp_numbers: [],
        email_addresses: [],
        quiet_hours_start: null,
        quiet_hours_end: null,
        cooldown_minutes: 5
      });
    }
  };

  const fetchAlertLog = async (clientId) => {
    try {
      const response = await axios.get(`${API}/alerts/log/${clientId}?limit=20`, { withCredentials: true });
      setAlertLog(response.data.logs || []);
    } catch (error) {
      console.error("Failed to fetch alert log:", error);
    }
  };

  const handleSaveSettings = async () => {
    if (!selectedClient || !settings) return;
    
    setSaving(true);
    try {
      await axios.put(`${API}/alerts/settings`, {
        client_id: selectedClient,
        ...settings
      }, { withCredentials: true });
      
      toast.success("Alert settings saved successfully");
    } catch (error) {
      toast.error("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleAddWhatsAppNumber = () => {
    if (!newWhatsAppNumber) return;
    
    // Validate phone number format
    const formatted = newWhatsAppNumber.startsWith('+') ? newWhatsAppNumber : `+${newWhatsAppNumber}`;
    
    if (settings.whatsapp_numbers?.includes(formatted)) {
      toast.error("Number already added");
      return;
    }
    
    setSettings({
      ...settings,
      whatsapp_numbers: [...(settings.whatsapp_numbers || []), formatted]
    });
    setNewWhatsAppNumber("");
  };

  const handleRemoveWhatsAppNumber = (number) => {
    setSettings({
      ...settings,
      whatsapp_numbers: settings.whatsapp_numbers.filter(n => n !== number)
    });
  };

  const handleSendTestAlert = async () => {
    if (!testNumber || !selectedClient) {
      toast.error("Please enter a phone number");
      return;
    }
    
    setSendingTest(true);
    try {
      const formatted = testNumber.startsWith('+') ? testNumber : `+${testNumber}`;
      const response = await axios.post(`${API}/alerts/test`, {
        client_id: selectedClient,
        phone_number: formatted
      }, { withCredentials: true });
      
      if (response.data.success) {
        toast.success("Test alert sent successfully!");
        fetchAlertLog(selectedClient);
      } else {
        toast.error(response.data.error || "Failed to send test alert");
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to send test alert");
    } finally {
      setSendingTest(false);
    }
  };

  const getClientName = (clientId) => {
    const client = clients.find(c => c.client_id === clientId);
    return client?.name || "Unknown";
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "N/A";
    return new Date(dateStr).toLocaleString();
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
    <div className="p-6 space-y-6" data-testid="admin-alerts-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            ALERT SETTINGS
          </h1>
          <p className="text-muted-foreground mt-1">
            Configure WhatsApp alerts for critical incidents
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

      {/* Service Status Banner */}
      <Card className={`border ${serviceStatus?.twilio_configured ? 'border-emerald-500/30 bg-emerald-500/5' : 'border-amber-500/30 bg-amber-500/5'}`}>
        <CardContent className="p-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {serviceStatus?.twilio_configured ? (
              <>
                <CheckCircle className="w-5 h-5 text-emerald-500" />
                <div>
                  <p className="font-medium text-emerald-400">Twilio WhatsApp Connected</p>
                  <p className="text-xs text-muted-foreground">From: {serviceStatus?.whatsapp_from}</p>
                </div>
              </>
            ) : (
              <>
                <AlertTriangle className="w-5 h-5 text-amber-500" />
                <div>
                  <p className="font-medium text-amber-400">Twilio Not Configured</p>
                  <p className="text-xs text-muted-foreground">Add credentials to enable WhatsApp alerts</p>
                </div>
              </>
            )}
          </div>
          {!serviceStatus?.twilio_configured && (
            <Button variant="outline" size="sm" className="text-amber-400 border-amber-500/30">
              Setup Guide
            </Button>
          )}
        </CardContent>
      </Card>

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
                      {client.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {selectedClient && settings && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Alert Configuration */}
          <div className="space-y-6">
            {/* Enable/Disable */}
            <Card className="bg-card/50 border-white/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Bell className="w-5 h-5 text-cyan-500" />
                  Alert Configuration
                </CardTitle>
                <CardDescription>
                  Configure when alerts should be sent for {getClientName(selectedClient)}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between p-4 rounded-lg bg-white/5 border border-white/10">
                  <div>
                    <p className="font-medium">Enable Alerts</p>
                    <p className="text-xs text-muted-foreground">Send notifications for incidents</p>
                  </div>
                  <Switch
                    checked={settings.enabled}
                    onCheckedChange={(checked) => setSettings({ ...settings, enabled: checked })}
                  />
                </div>

                <div className="space-y-4">
                  <Label>Alert Triggers</Label>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-red-500" />
                        <span>Critical Incidents</span>
                      </div>
                      <Switch
                        checked={settings.alert_on_critical}
                        onCheckedChange={(checked) => setSettings({ ...settings, alert_on_critical: checked })}
                        disabled={!settings.enabled}
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className="w-3 h-3 rounded-full bg-amber-500" />
                        <span>Warning Incidents</span>
                      </div>
                      <Switch
                        checked={settings.alert_on_warning}
                        onCheckedChange={(checked) => setSettings({ ...settings, alert_on_warning: checked })}
                        disabled={!settings.enabled}
                      />
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <Label>Cooldown Period (minutes)</Label>
                  <Select
                    value={String(settings.cooldown_minutes || 5)}
                    onValueChange={(value) => setSettings({ ...settings, cooldown_minutes: parseInt(value) })}
                    disabled={!settings.enabled}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="1">1 minute</SelectItem>
                      <SelectItem value="5">5 minutes</SelectItem>
                      <SelectItem value="10">10 minutes</SelectItem>
                      <SelectItem value="15">15 minutes</SelectItem>
                      <SelectItem value="30">30 minutes</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Minimum time between alerts for the same camera
                  </p>
                </div>

                <div className="space-y-4">
                  <Label>Quiet Hours (optional)</Label>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-xs text-muted-foreground">Start</Label>
                      <Input
                        type="time"
                        value={settings.quiet_hours_start || ""}
                        onChange={(e) => setSettings({ ...settings, quiet_hours_start: e.target.value })}
                        disabled={!settings.enabled}
                      />
                    </div>
                    <div>
                      <Label className="text-xs text-muted-foreground">End</Label>
                      <Input
                        type="time"
                        value={settings.quiet_hours_end || ""}
                        onChange={(e) => setSettings({ ...settings, quiet_hours_end: e.target.value })}
                        disabled={!settings.enabled}
                      />
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    No alerts will be sent during quiet hours
                  </p>
                </div>
              </CardContent>
            </Card>

            {/* WhatsApp Numbers */}
            <Card className="bg-card/50 border-white/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="w-5 h-5 text-emerald-500" />
                  WhatsApp Numbers
                </CardTitle>
                <CardDescription>
                  Numbers that will receive WhatsApp alerts
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex gap-2">
                  <Input
                    placeholder="+1234567890"
                    value={newWhatsAppNumber}
                    onChange={(e) => setNewWhatsAppNumber(e.target.value)}
                    disabled={!settings.enabled}
                  />
                  <Button
                    onClick={handleAddWhatsAppNumber}
                    disabled={!settings.enabled || !newWhatsAppNumber}
                    size="icon"
                  >
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>

                <div className="space-y-2">
                  {settings.whatsapp_numbers?.length > 0 ? (
                    settings.whatsapp_numbers.map((number, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-3 rounded-lg bg-white/5 border border-white/10"
                      >
                        <div className="flex items-center gap-2">
                          <MessageSquare className="w-4 h-4 text-emerald-500" />
                          <span className="font-mono">{number}</span>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleRemoveWhatsAppNumber(number)}
                          className="h-8 w-8"
                        >
                          <Trash2 className="w-4 h-4 text-red-400" />
                        </Button>
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      No WhatsApp numbers configured
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Test & Log */}
          <div className="space-y-6">
            {/* Test Alert */}
            <Card className="bg-card/50 border-white/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Send className="w-5 h-5 text-blue-500" />
                  Send Test Alert
                </CardTitle>
                <CardDescription>
                  Test your WhatsApp alert configuration
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Phone Number</Label>
                  <Input
                    placeholder="+1234567890"
                    value={testNumber}
                    onChange={(e) => setTestNumber(e.target.value)}
                  />
                </div>
                <Button
                  onClick={handleSendTestAlert}
                  disabled={sendingTest || !serviceStatus?.twilio_configured}
                  className="w-full"
                >
                  {sendingTest ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Sending...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4 mr-2" />
                      Send Test Alert
                    </>
                  )}
                </Button>
                {!serviceStatus?.twilio_configured && (
                  <p className="text-xs text-amber-400 text-center">
                    Configure Twilio credentials to send test alerts
                  </p>
                )}
              </CardContent>
            </Card>

            {/* Alert Log */}
            <Card className="bg-card/50 border-white/5">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Clock className="w-5 h-5 text-purple-500" />
                  Recent Alerts
                </CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <ScrollArea className="h-[400px]">
                  {alertLog.length > 0 ? (
                    <div className="divide-y divide-white/5">
                      {alertLog.map((log, idx) => (
                        <div key={idx} className="p-4 hover:bg-white/[0.02]">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              {log.success ? (
                                <CheckCircle className="w-4 h-4 text-emerald-500" />
                              ) : (
                                <XCircle className="w-4 h-4 text-red-500" />
                              )}
                              <span className="font-mono text-sm">{log.recipient}</span>
                            </div>
                            <Badge variant="outline" className={log.is_test ? "text-blue-400" : ""}>
                              {log.is_test ? "Test" : log.channel}
                            </Badge>
                          </div>
                          <p className="text-xs text-muted-foreground">
                            {formatDate(log.created_at)}
                          </p>
                          {log.error && (
                            <p className="text-xs text-red-400 mt-1">{log.error}</p>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="p-8 text-center text-muted-foreground">
                      <Bell className="w-12 h-12 mx-auto mb-3 opacity-30" />
                      <p>No alerts sent yet</p>
                    </div>
                  )}
                </ScrollArea>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Setup Instructions */}
      {!serviceStatus?.twilio_configured && (
        <Card className="bg-card/50 border-amber-500/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-amber-400">
              <Shield className="w-5 h-5" />
              Twilio Setup Instructions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ol className="list-decimal list-inside space-y-2 text-sm text-muted-foreground">
              <li>Create a Twilio account at <a href="https://www.twilio.com/" target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:underline">twilio.com</a></li>
              <li>Enable WhatsApp Sandbox in Twilio Console → Messaging → Try it out → Send a WhatsApp message</li>
              <li>Get your Account SID and Auth Token from Twilio Console Dashboard</li>
              <li>Add to <code className="px-1 py-0.5 bg-white/10 rounded">backend/.env</code>:
                <pre className="mt-2 p-3 bg-black/30 rounded text-xs overflow-x-auto">
{`TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886`}
                </pre>
              </li>
              <li>Restart the backend server</li>
              <li>For production, upgrade to a Twilio WhatsApp Business number</li>
            </ol>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
