import { useState, useEffect } from "react";
import axios from "axios";
import { 
  Server, 
  Plus, 
  RefreshCw, 
  Copy, 
  Check,
  Wifi,
  WifiOff,
  Cpu,
  HardDrive,
  Camera,
  Clock,
  AlertTriangle,
  Pencil,
  Trash2,
  MoreHorizontal,
  Power,
  PowerOff
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Badge } from "../../components/ui/badge";
import { ScrollArea } from "../../components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../../components/ui/dropdown-menu";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../../components/ui/alert-dialog";
import { motion } from "framer-motion";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem("session_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export default function AdminEdgeDevices() {
  const [devices, setDevices] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  
  // Provision dialog
  const [showProvisionDialog, setShowProvisionDialog] = useState(false);
  const [selectedClientId, setSelectedClientId] = useState("");
  const [deviceName, setDeviceName] = useState("");
  const [provisioning, setProvisioning] = useState(false);
  
  // Credentials dialog (shown after provisioning)
  const [showCredentialsDialog, setShowCredentialsDialog] = useState(false);
  const [newCredentials, setNewCredentials] = useState(null);
  const [copiedField, setCopiedField] = useState(null);
  
  // Edit dialog
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editingDevice, setEditingDevice] = useState(null);
  const [saving, setSaving] = useState(false);
  
  // Delete confirmation
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deviceToDelete, setDeviceToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [devicesRes, clientsRes] = await Promise.all([
        axios.get(`${API}/admin/edge-devices`, { 
          withCredentials: true,
          headers: getAuthHeaders()
        }),
        axios.get(`${API}/admin/clients`, { 
          withCredentials: true,
          headers: getAuthHeaders()
        })
      ]);
      
      setDevices(devicesRes.data.devices || []);
      setClients(clientsRes.data.clients || []);
    } catch (error) {
      console.error("Failed to fetch data:", error);
      toast.error("Failed to load edge devices");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const handleProvision = async () => {
    if (!selectedClientId) {
      toast.error("Please select a client");
      return;
    }
    if (!deviceName.trim()) {
      toast.error("Please enter a device name");
      return;
    }

    setProvisioning(true);
    try {
      const response = await axios.post(
        `${API}/admin/edge-devices/provision`,
        null,
        {
          params: {
            client_id: selectedClientId,
            device_name: deviceName
          },
          withCredentials: true,
          headers: getAuthHeaders()
        }
      );

      if (response.data.success) {
        setNewCredentials(response.data);
        setShowProvisionDialog(false);
        setShowCredentialsDialog(true);
        fetchData();
        toast.success("Edge device provisioned successfully!");
      } else {
        toast.error(response.data.message || "Failed to provision device");
      }
    } catch (error) {
      console.error("Provisioning error:", error);
      toast.error(error.response?.data?.detail || "Failed to provision device");
    } finally {
      setProvisioning(false);
    }
  };

  const handleEditDevice = (device) => {
    setEditingDevice({
      device_id: device.device_id,
      device_name: device.device_name || "",
      is_active: device.is_active !== false
    });
    setShowEditDialog(true);
  };

  const handleSaveEdit = async () => {
    if (!editingDevice) return;
    
    setSaving(true);
    try {
      const response = await axios.put(
        `${API}/admin/edge-devices/${editingDevice.device_id}`,
        {
          device_name: editingDevice.device_name,
          is_active: editingDevice.is_active
        },
        {
          withCredentials: true,
          headers: getAuthHeaders()
        }
      );
      
      if (response.data.success) {
        toast.success("Device updated successfully");
        setShowEditDialog(false);
        setEditingDevice(null);
        fetchData();
      }
    } catch (error) {
      console.error("Failed to update device:", error);
      toast.error(error.response?.data?.detail || "Failed to update device");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteClick = (device) => {
    setDeviceToDelete(device);
    setShowDeleteDialog(true);
  };

  const handleConfirmDelete = async () => {
    if (!deviceToDelete) return;
    
    setDeleting(true);
    try {
      const response = await axios.delete(
        `${API}/admin/edge-devices/${deviceToDelete.device_id}`,
        {
          withCredentials: true,
          headers: getAuthHeaders()
        }
      );
      
      if (response.data.success) {
        toast.success("Device deleted successfully");
        setShowDeleteDialog(false);
        setDeviceToDelete(null);
        fetchData();
      }
    } catch (error) {
      console.error("Failed to delete device:", error);
      toast.error(error.response?.data?.detail || "Failed to delete device");
    } finally {
      setDeleting(false);
    }
  };

  const handleToggleActive = async (device) => {
    try {
      const response = await axios.put(
        `${API}/admin/edge-devices/${device.device_id}`,
        {
          is_active: !device.is_active
        },
        {
          withCredentials: true,
          headers: getAuthHeaders()
        }
      );
      
      if (response.data.success) {
        toast.success(device.is_active ? "Device deactivated" : "Device activated");
        fetchData();
      }
    } catch (error) {
      toast.error("Failed to update device status");
    }
  };

  const copyToClipboard = (text, field) => {
    navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
    toast.success("Copied to clipboard!");
  };

  const formatLastSeen = (timestamp) => {
    if (!timestamp) return "Never";
    const date = new Date(timestamp);
    const now = new Date();
    const diff = (now - date) / 1000; // seconds
    
    if (diff < 60) return "Just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString();
  };

  if (loading) {
    return (
      <div className="p-6 space-y-6" data-testid="edge-devices-loading">
        <div className="flex items-center justify-between">
          <div className="skeleton h-8 w-48" />
          <div className="skeleton h-10 w-40" />
        </div>
        <div className="grid gap-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="skeleton h-32 w-full rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6" data-testid="admin-edge-devices">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            EDGE DEVICES
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage on-premise ML processors
          </p>
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </Button>
          <Button
            onClick={() => {
              setDeviceName("");
              setSelectedClientId("");
              setShowProvisionDialog(true);
            }}
            className="bg-blue-600 hover:bg-blue-700"
            data-testid="provision-device-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Provision New Device
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-md bg-blue-500/10 border border-blue-500/30">
                <Server className="w-5 h-5 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{devices.length}</p>
                <p className="text-sm text-muted-foreground">Total Devices</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-md bg-emerald-500/10 border border-emerald-500/30">
                <Wifi className="w-5 h-5 text-emerald-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{devices.filter(d => d.is_online).length}</p>
                <p className="text-sm text-muted-foreground">Online</p>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-md bg-amber-500/10 border border-amber-500/30">
                <WifiOff className="w-5 h-5 text-amber-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{devices.filter(d => !d.is_online).length}</p>
                <p className="text-sm text-muted-foreground">Offline</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Device List */}
      <Card className="bg-card/50 border-white/5">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            <Server className="w-5 h-5 text-blue-500" />
            REGISTERED DEVICES
          </CardTitle>
        </CardHeader>
        <CardContent>
          {devices.length === 0 ? (
            <div className="text-center py-12">
              <Server className="w-16 h-16 mx-auto mb-4 text-muted-foreground/30" />
              <h3 className="text-lg font-semibold mb-2">No Edge Devices</h3>
              <p className="text-muted-foreground mb-4">
                Provision your first edge device to start processing video feeds
              </p>
              <Button onClick={() => setShowProvisionDialog(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Provision Device
              </Button>
            </div>
          ) : (
            <ScrollArea className="h-[500px]">
              <div className="space-y-4">
                {devices.map((device, idx) => (
                  <motion.div
                    key={device.device_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="p-4 rounded-lg border border-white/5 bg-white/[0.02] hover:bg-white/[0.04] transition-colors"
                    data-testid={`device-${device.device_id}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex items-start gap-4">
                        <div className={`p-3 rounded-md ${device.is_online ? 'bg-emerald-500/10 border border-emerald-500/30' : 'bg-gray-500/10 border border-gray-500/30'}`}>
                          <Server className={`w-6 h-6 ${device.is_online ? 'text-emerald-500' : 'text-gray-500'}`} />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="font-semibold">{device.device_name || device.device_id}</h3>
                            <Badge 
                              variant="outline" 
                              className={device.is_online 
                                ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/30' 
                                : 'bg-gray-500/10 text-gray-500 border-gray-500/30'
                              }
                            >
                              {device.is_online ? 'Online' : 'Offline'}
                            </Badge>
                            {device.is_active === false && (
                              <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/30">
                                Disabled
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-muted-foreground mt-1">
                            Client: {device.client_name || device.client_id}
                          </p>
                          <p className="text-xs text-muted-foreground mt-1 font-mono">
                            ID: {device.device_id}
                          </p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-2">
                        <div className="text-right text-sm mr-4">
                          <div className="flex items-center gap-1 text-muted-foreground">
                            <Clock className="w-3 h-3" />
                            <span>Last seen: {formatLastSeen(device.last_heartbeat)}</span>
                          </div>
                        </div>
                        
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                              <MoreHorizontal className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => handleEditDevice(device)}>
                              <Pencil className="w-4 h-4 mr-2" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem onClick={() => handleToggleActive(device)}>
                              {device.is_active !== false ? (
                                <>
                                  <PowerOff className="w-4 h-4 mr-2 text-amber-500" />
                                  <span className="text-amber-500">Deactivate</span>
                                </>
                              ) : (
                                <>
                                  <Power className="w-4 h-4 mr-2 text-emerald-500" />
                                  <span className="text-emerald-500">Activate</span>
                                </>
                              )}
                            </DropdownMenuItem>
                            <DropdownMenuItem 
                              onClick={() => handleDeleteClick(device)}
                              className="text-red-500"
                            >
                              <Trash2 className="w-4 h-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </div>
                    </div>
                    
                    {/* Device Stats (if online) */}
                    {device.is_online && (
                      <div className="mt-4 pt-4 border-t border-white/5 grid grid-cols-4 gap-4">
                        <div className="flex items-center gap-2">
                          <Cpu className="w-4 h-4 text-cyan-400" />
                          <div>
                            <p className="text-xs text-muted-foreground">CPU</p>
                            <p className="font-medium">{device.cpu_usage?.toFixed(1) || 0}%</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <HardDrive className="w-4 h-4 text-purple-400" />
                          <div>
                            <p className="text-xs text-muted-foreground">Memory</p>
                            <p className="font-medium">{device.memory_usage?.toFixed(1) || 0}%</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Camera className="w-4 h-4 text-blue-400" />
                          <div>
                            <p className="text-xs text-muted-foreground">Cameras</p>
                            <p className="font-medium">{device.cameras_online || 0}/{device.cameras_total || 0}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-amber-400" />
                          <div>
                            <p className="text-xs text-muted-foreground">Last Incident</p>
                            <p className="font-medium">{formatLastSeen(device.last_incident_at)}</p>
                          </div>
                        </div>
                      </div>
                    )}
                  </motion.div>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      {/* Provision Dialog */}
      <Dialog open={showProvisionDialog} onOpenChange={setShowProvisionDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Rajdhani, sans-serif' }}>
              PROVISION NEW EDGE DEVICE
            </DialogTitle>
            <DialogDescription>
              Create credentials for a new on-premise edge device
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="client">Select Client *</Label>
              <Select value={selectedClientId} onValueChange={setSelectedClientId}>
                <SelectTrigger data-testid="client-select">
                  <SelectValue placeholder="Choose a client..." />
                </SelectTrigger>
                <SelectContent>
                  {clients.map((client) => (
                    <SelectItem key={client.client_id} value={client.client_id}>
                      {client.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label htmlFor="deviceName">Device Name *</Label>
              <Input
                id="deviceName"
                placeholder="e.g., Store-Mumbai-001"
                value={deviceName}
                onChange={(e) => setDeviceName(e.target.value)}
                data-testid="device-name-input"
              />
              <p className="text-xs text-muted-foreground">
                A friendly name to identify this edge device
              </p>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowProvisionDialog(false)}>
              Cancel
            </Button>
            <Button 
              onClick={handleProvision} 
              disabled={provisioning}
              className="bg-blue-600 hover:bg-blue-700"
              data-testid="confirm-provision-btn"
            >
              {provisioning ? (
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Plus className="w-4 h-4 mr-2" />
              )}
              Provision Device
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Credentials Dialog */}
      <Dialog open={showCredentialsDialog} onOpenChange={setShowCredentialsDialog}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-emerald-500" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
              <Check className="w-5 h-5" />
              DEVICE PROVISIONED SUCCESSFULLY
            </DialogTitle>
            <DialogDescription>
              <span className="text-amber-400 font-semibold">⚠️ IMPORTANT:</span> Copy these credentials now. The API key will NOT be shown again!
            </DialogDescription>
          </DialogHeader>
          
          {newCredentials && (
            <div className="space-y-4 py-4">
              {/* Device ID */}
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Device ID</Label>
                <div className="flex items-center gap-2">
                  <code className="flex-1 p-3 rounded-md bg-black/50 border border-white/10 text-sm font-mono break-all">
                    {newCredentials.device_id}
                  </code>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(newCredentials.device_id, 'device_id')}
                  >
                    {copiedField === 'device_id' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </Button>
                </div>
              </div>
              
              {/* Client ID */}
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Client ID</Label>
                <div className="flex items-center gap-2">
                  <code className="flex-1 p-3 rounded-md bg-black/50 border border-white/10 text-sm font-mono break-all">
                    {newCredentials.client_id}
                  </code>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(newCredentials.client_id, 'client_id')}
                  >
                    {copiedField === 'client_id' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </Button>
                </div>
              </div>
              
              {/* API Key */}
              <div className="space-y-2">
                <Label className="text-xs text-amber-400">API Key (shown only once!)</Label>
                <div className="flex items-center gap-2">
                  <code className="flex-1 p-3 rounded-md bg-amber-500/10 border border-amber-500/30 text-sm font-mono break-all text-amber-400">
                    {newCredentials.api_key}
                  </code>
                  <Button
                    size="sm"
                    variant="outline"
                    className="border-amber-500/50"
                    onClick={() => copyToClipboard(newCredentials.api_key, 'api_key')}
                  >
                    {copiedField === 'api_key' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </Button>
                </div>
              </div>
              
              {/* Central Server URL */}
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Central Server URL</Label>
                <div className="flex items-center gap-2">
                  <code className="flex-1 p-3 rounded-md bg-black/50 border border-white/10 text-sm font-mono break-all">
                    {newCredentials.central_server_url}
                  </code>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(newCredentials.central_server_url, 'url')}
                  >
                    {copiedField === 'url' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  </Button>
                </div>
              </div>

              {/* Copy All Button */}
              <Button
                className="w-full mt-4"
                variant="outline"
                onClick={() => {
                  const envContent = `# Edge Device Configuration
CENTRAL_SERVER_URL=${newCredentials.central_server_url}
CLIENT_ID=${newCredentials.client_id}
API_KEY=${newCredentials.api_key}
DEVICE_NAME=${deviceName || 'Edge-Device'}

# Add your Emergent LLM Key for AI analysis
EMERGENT_LLM_KEY=your-emergent-key-here

# Your RTSP Cameras (comma-separated)
CAMERAS=rtsp://admin:password@192.168.1.100:554/stream1

# Detection Settings
DETECTION_INTERVAL=1.0
CONFIDENCE_THRESHOLD=0.6
ENABLE_POSE_DETECTION=true
ENABLE_FACE_RECOGNITION=true
ENABLE_GPT_ANALYSIS=true
HEARTBEAT_INTERVAL_SECONDS=60`;
                  copyToClipboard(envContent, 'all');
                }}
                data-testid="copy-env-btn"
              >
                <Copy className="w-4 h-4 mr-2" />
                Copy as .env file content
              </Button>
            </div>
          )}
          
          <DialogFooter>
            <Button onClick={() => setShowCredentialsDialog(false)} className="w-full">
              I've Saved the Credentials
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Rajdhani, sans-serif' }}>
              EDIT EDGE DEVICE
            </DialogTitle>
            <DialogDescription>
              Update device settings
            </DialogDescription>
          </DialogHeader>
          
          {editingDevice && (
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Device ID</Label>
                <Input value={editingDevice.device_id} disabled className="font-mono text-sm" />
              </div>
              
              <div className="space-y-2">
                <Label>Device Name</Label>
                <Input
                  value={editingDevice.device_name}
                  onChange={(e) => setEditingDevice({ ...editingDevice, device_name: e.target.value })}
                  placeholder="Enter device name"
                />
              </div>
              
              <div className="flex items-center justify-between p-4 rounded-lg bg-white/[0.02] border border-white/5">
                <div>
                  <p className="font-medium">Active</p>
                  <p className="text-sm text-muted-foreground">Device can connect and send data</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={editingDevice.is_active}
                    onChange={(e) => setEditingDevice({ ...editingDevice, is_active: e.target.checked })}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
                </label>
              </div>
            </div>
          )}
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveEdit} disabled={saving}>
              {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : null}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Edge Device?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete <strong>{deviceToDelete?.device_name || deviceToDelete?.device_id}</strong>?
              <br /><br />
              This action cannot be undone. The device will need to be re-provisioned to reconnect.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              disabled={deleting}
              className="bg-red-600 hover:bg-red-700"
            >
              {deleting ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Trash2 className="w-4 h-4 mr-2" />}
              Delete Device
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
