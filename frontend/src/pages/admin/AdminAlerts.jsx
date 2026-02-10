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
  Shield,
  Settings,
  Eye,
  EyeOff,
  ExternalLink
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import { toast } from "sonner";
import { motion } from "framer-motion";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const getAuthHeaders = () => {
  const token = localStorage.getItem("session_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export default function AdminAlerts() {
  const [clients, setClients] = useState([]);
  const [selectedClient, setSelectedClient] = useState(null);
  const [settings, setSettings] = useState(null);
  const [twilioConfig, setTwilioConfig] = useState(null);
  const [alertLog, setAlertLog] = useState([]);
  const [alertStatus, setAlertStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  
  // Twilio form
  const [twilioForm, setTwilioForm] = useState({
    account_sid: "",
    auth_token: "",
    whatsapp_from: "",
    enabled: false
  });
  const [showAuthToken, setShowAuthToken] = useState(false);
  const [savingTwilio, setSavingTwilio] = useState(false);
  
  // Test message
  const [testNumber, setTestNumber] = useState("");
  const [testMessage, setTestMessage] = useState("Test alert from SecureGuard AI");
  const [sendingTest, setSendingTest] = useState(false);
  
  // WhatsApp numbers
  const [newWhatsAppNumber, setNewWhatsAppNumber] = useState("");

  useEffect(() => {
    fetchClients();
    fetchAlertStatus();
  }, []);

  useEffect(() => {
    if (selectedClient) {
      fetchClientSettings(selectedClient);
      fetchTwilioConfig(selectedClient);
      fetchAlertLog(selectedClient);
    }
  }, [selectedClient]);

  const fetchClients = async () => {
    try {
      const response = await axios.get(`${API}/admin/clients?limit=100`, { 
        withCredentials: true,
        headers: getAuthHeaders()
      });
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

  const fetchAlertStatus = async () => {
    try {
      const response = await axios.get(`${API}/alerts/status`, { 
        withCredentials: true,
        headers: getAuthHeaders()
      });
      setAlertStatus(response.data);
    } catch (error) {
      console.error("Failed to fetch alert status:", error);
    }
  };

  const fetchClientSettings = async (clientId) => {
    try {
      const response = await axios.get(`${API}/alerts/settings/${clientId}`, { 
        withCredentials: true,
        headers: getAuthHeaders()
      });
      setSettings(response.data);
    } catch (error) {
      console.error("Failed to fetch alert settings:", error);
      setSettings({
        alert_on_critical: true,
        alert_on_warning: false,
        alert_email: true,
        whatsapp_numbers: [],
        detection_sensitivity: "medium"
      });
    }
  };

  const fetchTwilioConfig = async (clientId) => {
    try {
      const response = await axios.get(`${API}/alerts/twilio/${clientId}`, { 
        withCredentials: true,
        headers: getAuthHeaders()
      });
      setTwilioConfig(response.data);
      setTwilioForm({
        account_sid: "",  // Don't show actual SID
        auth_token: "",   // Don't show actual token
        whatsapp_from: response.data.whatsapp_from || "",
        enabled: response.data.enabled || false
      });
    } catch (error) {
      console.error("Failed to fetch Twilio config:", error);
      setTwilioConfig(null);
    }
  };

  const fetchAlertLog = async (clientId) => {
    try {
      const response = await axios.get(`${API}/alerts/log/${clientId}?limit=20`, { 
        withCredentials: true,
        headers: getAuthHeaders()
      });
      setAlertLog(response.data.alerts || []);
    } catch (error) {
      console.error("Failed to fetch alert log:", error);
      setAlertLog([]);
    }
  };

  const handleSaveSettings = async () => {
    if (!selectedClient || !settings) return;
    
    setSaving(true);
    try {
      await axios.put(`${API}/alerts/settings/${selectedClient}`, settings, { 
        withCredentials: true,
        headers: getAuthHeaders()
      });
      toast.success("Alert settings saved successfully");
    } catch (error) {
      toast.error("Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveTwilioConfig = async () => {
    if (!selectedClient) return;
    
    setSavingTwilio(true);
    try {
      const payload = {
        whatsapp_from: twilioForm.whatsapp_from,
        enabled: twilioForm.enabled,
        whatsapp_numbers: settings?.whatsapp_numbers || []
      };
      
      // Only include credentials if they were entered
      if (twilioForm.account_sid) {
        payload.account_sid = twilioForm.account_sid;
      }
      if (twilioForm.auth_token) {
        payload.auth_token = twilioForm.auth_token;
      }
      
      await axios.put(`${API}/alerts/twilio/${selectedClient}`, payload, { 
        withCredentials: true,
        headers: getAuthHeaders()
      });
      
      toast.success("Twilio configuration saved successfully");
      fetchTwilioConfig(selectedClient);
      
      // Clear sensitive fields
      setTwilioForm(prev => ({
        ...prev,
        account_sid: "",
        auth_token: ""
      }));
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to save Twilio configuration");
    } finally {
      setSavingTwilio(false);
    }
  };

  const handleAddWhatsAppNumber = () => {
    if (!newWhatsAppNumber) return;
    
    let formatted = newWhatsAppNumber.trim();
    if (!formatted.startsWith('+')) {
      formatted = `+${formatted}`;
    }
    
    if (settings?.whatsapp_numbers?.includes(formatted)) {
      toast.error("Number already added");
      return;
    }
    
    setSettings({
      ...settings,
      whatsapp_numbers: [...(settings?.whatsapp_numbers || []), formatted]
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
      let formatted = testNumber.trim();
      if (!formatted.startsWith('+')) {
        formatted = `+${formatted}`;
      }
      
      const response = await axios.post(`${API}/alerts/twilio/${selectedClient}/test`, {
        to_number: formatted,
        message: testMessage
      }, { 
        withCredentials: true,
        headers: getAuthHeaders()
      });
      
      if (response.data.success) {
        toast.success(`Test alert sent! Message SID: ${response.data.message_sid}`);
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
            ALERT CONFIGURATION
          </h1>
          <p className="text-muted-foreground mt-1">
            Configure WhatsApp alerts via Twilio for critical incidents
          </p>
        </div>
      </div>

      {/* Alert Status Summary */}
      {alertStatus && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-card/50 border-white/5">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-emerald-500/10 border border-emerald-500/30">
                  <CheckCircle className="w-5 h-5 text-emerald-500" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Status</p>
                  <p className="font-semibold capitalize">{alertStatus.status}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-card/50 border-white/5">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-red-500/10 border border-red-500/30">
                  <AlertTriangle className="w-5 h-5 text-red-500" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Critical (24h)</p>
                  <p className="font-semibold">{alertStatus.alerts_24h?.critical || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-card/50 border-white/5">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-amber-500/10 border border-amber-500/30">
                  <Bell className="w-5 h-5 text-amber-500" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Warnings (24h)</p>
                  <p className="font-semibold">{alertStatus.alerts_24h?.warning || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card className="bg-card/50 border-white/5">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-blue-500/10 border border-blue-500/30">
                  <MessageSquare className="w-5 h-5 text-blue-500" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground">Total (24h)</p>
                  <p className="font-semibold">{alertStatus.alerts_24h?.total || 0}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Client Selector */}
      <Card className="bg-card/50 border-white/5">
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <Building2 className="w-5 h-5 text-muted-foreground" />
            <div className="flex-1">
              <Label className="text-xs text-muted-foreground uppercase tracking-wider">
                Select Client to Configure
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

      {selectedClient && (
        <Tabs defaultValue="twilio" className="space-y-6">
          <TabsList className="bg-card/50 border border-white/10">
            <TabsTrigger value="twilio" className="data-[state=active]:bg-white/10">
              <MessageSquare className="w-4 h-4 mr-2" />
              Twilio Setup
            </TabsTrigger>
            <TabsTrigger value="settings" className="data-[state=active]:bg-white/10">
              <Settings className="w-4 h-4 mr-2" />
              Alert Settings
            </TabsTrigger>
            <TabsTrigger value="test" className="data-[state=active]:bg-white/10">
              <Send className="w-4 h-4 mr-2" />
              Test & Logs
            </TabsTrigger>
          </TabsList>

          {/* Twilio Setup Tab */}
          <TabsContent value="twilio">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Twilio Credentials */}
              <Card className="bg-card/50 border-white/5">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="w-5 h-5 text-emerald-500" />
                    Twilio Credentials
                  </CardTitle>
                  <CardDescription>
                    Enter your Twilio account credentials for {getClientName(selectedClient)}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Status Badge */}
                  <div className="flex items-center gap-2 p-3 rounded-lg bg-white/5">
                    {twilioConfig?.configured ? (
                      <>
                        <CheckCircle className="w-4 h-4 text-emerald-500" />
                        <span className="text-emerald-400">Twilio Configured</span>
                        <Badge variant="outline" className="ml-auto">
                          {twilioConfig.account_sid_masked}
                        </Badge>
                      </>
                    ) : (
                      <>
                        <XCircle className="w-4 h-4 text-amber-500" />
                        <span className="text-amber-400">Not Configured</span>
                      </>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label>Account SID</Label>
                    <Input
                      placeholder={twilioConfig?.configured ? "••••••••••••••••••••" : "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"}
                      value={twilioForm.account_sid}
                      onChange={(e) => setTwilioForm({...twilioForm, account_sid: e.target.value})}
                    />
                    <p className="text-xs text-muted-foreground">
                      {twilioConfig?.configured ? "Leave blank to keep existing" : "Find in Twilio Console Dashboard"}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label>Auth Token</Label>
                    <div className="relative">
                      <Input
                        type={showAuthToken ? "text" : "password"}
                        placeholder={twilioConfig?.configured ? "••••••••••••••••••••" : "Your auth token"}
                        value={twilioForm.auth_token}
                        onChange={(e) => setTwilioForm({...twilioForm, auth_token: e.target.value})}
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute right-2 top-1/2 -translate-y-1/2 h-7 w-7 p-0"
                        onClick={() => setShowAuthToken(!showAuthToken)}
                      >
                        {showAuthToken ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {twilioConfig?.configured ? "Leave blank to keep existing" : "Find in Twilio Console Dashboard"}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label>WhatsApp From Number</Label>
                    <Input
                      placeholder="whatsapp:+14155238886"
                      value={twilioForm.whatsapp_from}
                      onChange={(e) => setTwilioForm({...twilioForm, whatsapp_from: e.target.value})}
                    />
                    <p className="text-xs text-muted-foreground">
                      Twilio Sandbox: whatsapp:+14155238886
                    </p>
                  </div>

                  <div className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                    <div>
                      <p className="font-medium">Enable WhatsApp Alerts</p>
                      <p className="text-xs text-muted-foreground">Send alerts via WhatsApp</p>
                    </div>
                    <Switch
                      checked={twilioForm.enabled}
                      onCheckedChange={(checked) => setTwilioForm({...twilioForm, enabled: checked})}
                    />
                  </div>

                  <Button 
                    onClick={handleSaveTwilioConfig} 
                    disabled={savingTwilio}
                    className="w-full"
                  >
                    {savingTwilio ? (
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    ) : (
                      <Save className="w-4 h-4 mr-2" />
                    )}
                    Save Twilio Configuration
                  </Button>
                </CardContent>
              </Card>

              {/* Setup Guide */}
              <Card className="bg-card/50 border-white/5">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <ExternalLink className="w-5 h-5 text-blue-500" />
                    Twilio Setup Guide
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ol className="list-decimal list-inside space-y-4 text-sm">
                    <li className="space-y-2">
                      <span className="font-medium">Create Twilio Account</span>
                      <p className="text-muted-foreground ml-5">
                        Go to <a href="https://www.twilio.com/try-twilio" target="_blank" rel="noopener noreferrer" className="text-cyan-400 hover:underline">twilio.com/try-twilio</a> and sign up for free
                      </p>
                    </li>
                    <li className="space-y-2">
                      <span className="font-medium">Get Credentials</span>
                      <p className="text-muted-foreground ml-5">
                        In Twilio Console Dashboard, copy your <strong>Account SID</strong> and <strong>Auth Token</strong>
                      </p>
                    </li>
                    <li className="space-y-2">
                      <span className="font-medium">Enable WhatsApp Sandbox</span>
                      <p className="text-muted-foreground ml-5">
                        Go to <strong>Messaging → Try it out → Send a WhatsApp message</strong>
                      </p>
                    </li>
                    <li className="space-y-2">
                      <span className="font-medium">Join Sandbox</span>
                      <p className="text-muted-foreground ml-5">
                        Send the join code to Twilio's WhatsApp number from your phone. Example: <code className="px-1 py-0.5 bg-white/10 rounded">join example-word</code>
                      </p>
                    </li>
                    <li className="space-y-2">
                      <span className="font-medium">Enter Credentials Above</span>
                      <p className="text-muted-foreground ml-5">
                        Paste your Account SID, Auth Token, and WhatsApp From number (sandbox: <code className="px-1 py-0.5 bg-white/10 rounded">whatsapp:+14155238886</code>)
                      </p>
                    </li>
                    <li className="space-y-2">
                      <span className="font-medium">Test Connection</span>
                      <p className="text-muted-foreground ml-5">
                        Go to the <strong>Test & Logs</strong> tab and send a test message
                      </p>
                    </li>
                  </ol>

                  <div className="p-4 rounded-lg bg-amber-500/10 border border-amber-500/30">
                    <p className="text-sm text-amber-400">
                      <strong>⚠️ Important:</strong> For Twilio Sandbox, recipients must first join by sending the join code to the WhatsApp number. For production, upgrade to a Twilio WhatsApp Business number.
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Alert Settings Tab */}
          <TabsContent value="settings">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="bg-card/50 border-white/5">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Bell className="w-5 h-5 text-cyan-500" />
                    Alert Triggers
                  </CardTitle>
                  <CardDescription>
                    Configure when alerts should be sent
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-red-500" />
                      <span>Critical Incidents</span>
                    </div>
                    <Switch
                      checked={settings?.alert_on_critical ?? true}
                      onCheckedChange={(checked) => setSettings({...settings, alert_on_critical: checked})}
                    />
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                    <div className="flex items-center gap-2">
                      <div className="w-3 h-3 rounded-full bg-amber-500" />
                      <span>Warning Incidents</span>
                    </div>
                    <Switch
                      checked={settings?.alert_on_warning ?? false}
                      onCheckedChange={(checked) => setSettings({...settings, alert_on_warning: checked})}
                    />
                  </div>
                  <div className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                    <div className="flex items-center gap-2">
                      <Mail className="w-4 h-4 text-blue-500" />
                      <span>Email Alerts</span>
                    </div>
                    <Switch
                      checked={settings?.alert_email ?? true}
                      onCheckedChange={(checked) => setSettings({...settings, alert_email: checked})}
                    />
                  </div>

                  <Button onClick={handleSaveSettings} disabled={saving} className="w-full">
                    {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Save className="w-4 h-4 mr-2" />}
                    Save Alert Settings
                  </Button>
                </CardContent>
              </Card>

              <Card className="bg-card/50 border-white/5">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <MessageSquare className="w-5 h-5 text-emerald-500" />
                    WhatsApp Recipients
                  </CardTitle>
                  <CardDescription>
                    Numbers that will receive WhatsApp alerts
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex gap-2">
                    <Input
                      placeholder="+919876543210"
                      value={newWhatsAppNumber}
                      onChange={(e) => setNewWhatsAppNumber(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && handleAddWhatsAppNumber()}
                    />
                    <Button onClick={handleAddWhatsAppNumber} size="icon">
                      <Plus className="w-4 h-4" />
                    </Button>
                  </div>

                  <div className="space-y-2 max-h-[200px] overflow-auto">
                    {settings?.whatsapp_numbers?.length > 0 ? (
                      settings.whatsapp_numbers.map((number, idx) => (
                        <div key={idx} className="flex items-center justify-between p-3 rounded-lg bg-white/5">
                          <div className="flex items-center gap-2">
                            <MessageSquare className="w-4 h-4 text-emerald-500" />
                            <span className="font-mono">{number}</span>
                          </div>
                          <Button variant="ghost" size="icon" onClick={() => handleRemoveWhatsAppNumber(number)} className="h-8 w-8">
                            <Trash2 className="w-4 h-4 text-red-400" />
                          </Button>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-muted-foreground text-center py-4">No numbers added</p>
                    )}
                  </div>

                  <p className="text-xs text-muted-foreground">
                    Remember to save both Alert Settings and Twilio Configuration after adding numbers
                  </p>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Test & Logs Tab */}
          <TabsContent value="test">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Send Test */}
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
                  {!twilioConfig?.configured && (
                    <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
                      <p className="text-sm text-amber-400">
                        ⚠️ Configure Twilio credentials first in the "Twilio Setup" tab
                      </p>
                    </div>
                  )}

                  <div className="space-y-2">
                    <Label>Recipient Phone Number</Label>
                    <Input
                      placeholder="+919876543210"
                      value={testNumber}
                      onChange={(e) => setTestNumber(e.target.value)}
                      disabled={!twilioConfig?.configured}
                    />
                    <p className="text-xs text-muted-foreground">
                      Include country code (e.g., +91 for India, +1 for USA)
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label>Test Message</Label>
                    <Input
                      placeholder="Test alert from SecureGuard AI"
                      value={testMessage}
                      onChange={(e) => setTestMessage(e.target.value)}
                      disabled={!twilioConfig?.configured}
                    />
                  </div>

                  <Button 
                    onClick={handleSendTestAlert} 
                    disabled={sendingTest || !twilioConfig?.configured || !testNumber}
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
                        Send Test WhatsApp Message
                      </>
                    )}
                  </Button>
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
                        {alertLog.map((alert, idx) => (
                          <div key={idx} className="p-4 hover:bg-white/[0.02]">
                            <div className="flex items-center justify-between mb-2">
                              <Badge variant="outline" className={
                                alert.severity === "critical" ? "text-red-400 border-red-500/30" :
                                alert.severity === "warning" ? "text-amber-400 border-amber-500/30" :
                                "text-blue-400 border-blue-500/30"
                              }>
                                {alert.severity || "info"}
                              </Badge>
                              <span className="text-xs text-muted-foreground">
                                {formatDate(alert.timestamp)}
                              </span>
                            </div>
                            <p className="text-sm line-clamp-2">{alert.description || "Alert triggered"}</p>
                            {alert.camera_name && (
                              <p className="text-xs text-muted-foreground mt-1">
                                Camera: {alert.camera_name}
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="p-8 text-center text-muted-foreground">
                        <Bell className="w-12 h-12 mx-auto mb-3 opacity-30" />
                        <p>No alerts yet</p>
                      </div>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}
