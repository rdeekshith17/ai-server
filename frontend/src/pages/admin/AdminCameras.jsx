import { useState, useEffect } from "react";
import axios from "axios";
import { 
  Camera, 
  Plus, 
  Search,
  MoreHorizontal,
  Pencil,
  Trash2,
  Power,
  PowerOff,
  Building2,
  MapPin,
  Activity,
  Settings2,
  Link,
  Wifi,
  WifiOff
} from "lucide-react";
import { Card, CardContent } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import { Switch } from "../../components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
import { Label } from "../../components/ui/label";
import { toast } from "sonner";
import { motion } from "framer-motion";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AdminCameras() {
  const [cameras, setCameras] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [clientFilter, setClientFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [editingCamera, setEditingCamera] = useState(null);
  const [newCamera, setNewCamera] = useState({
    client_id: "",
    name: "",
    location: "",
    rtsp_url: "",
    detection_enabled: true,
    sensitivity: "medium"
  });

  useEffect(() => {
    fetchCameras();
    fetchClients();
  }, [clientFilter, statusFilter]);

  const fetchCameras = async () => {
    try {
      const params = new URLSearchParams();
      if (clientFilter && clientFilter !== "all") params.append("client_id", clientFilter);
      if (statusFilter && statusFilter !== "all") params.append("status", statusFilter);
      
      const response = await axios.get(`${API}/admin/cameras?${params}`, { withCredentials: true });
      setCameras(response.data.cameras || []);
    } catch (error) {
      console.error("Failed to fetch cameras:", error);
      toast.error("Failed to load cameras");
    } finally {
      setLoading(false);
    }
  };

  const fetchClients = async () => {
    try {
      const response = await axios.get(`${API}/admin/clients?limit=100`, { withCredentials: true });
      setClients(response.data.clients || []);
    } catch (error) {
      console.error("Failed to fetch clients:", error);
    }
  };

  const handleAddCamera = async () => {
    try {
      if (!newCamera.client_id || !newCamera.name || !newCamera.location) {
        toast.error("Please fill in all required fields");
        return;
      }

      const response = await axios.post(`${API}/admin/cameras`, newCamera, { withCredentials: true });
      
      if (response.data.success) {
        toast.success("Camera created successfully");
        setShowAddDialog(false);
        resetForm();
        fetchCameras();
      }
    } catch (error) {
      console.error("Failed to create camera:", error);
      toast.error(error.response?.data?.detail || "Failed to create camera");
    }
  };

  const handleUpdateCamera = async () => {
    try {
      const response = await axios.put(
        `${API}/admin/cameras/${editingCamera.camera_id}`, 
        editingCamera, 
        { withCredentials: true }
      );
      
      if (response.data.success) {
        toast.success("Camera updated successfully");
        setEditingCamera(null);
        fetchCameras();
      }
    } catch (error) {
      toast.error("Failed to update camera");
    }
  };

  const handleDeleteCamera = async (cameraId) => {
    if (!window.confirm("Are you sure you want to delete this camera?")) return;
    
    try {
      await axios.delete(`${API}/admin/cameras/${cameraId}`, { withCredentials: true });
      toast.success("Camera deleted");
      fetchCameras();
    } catch (error) {
      toast.error("Failed to delete camera");
    }
  };

  const handleToggleStatus = async (camera) => {
    try {
      const newStatus = camera.status === "online" ? "disabled" : "online";
      await axios.put(
        `${API}/admin/cameras/${camera.camera_id}`,
        { status: newStatus },
        { withCredentials: true }
      );
      toast.success(`Camera ${newStatus === "online" ? "enabled" : "disabled"}`);
      fetchCameras();
    } catch (error) {
      toast.error("Failed to update camera status");
    }
  };

  const resetForm = () => {
    setNewCamera({
      client_id: "",
      name: "",
      location: "",
      rtsp_url: "",
      detection_enabled: true,
      sensitivity: "medium"
    });
  };

  const filteredCameras = cameras.filter(camera => 
    camera.name?.toLowerCase().includes(search.toLowerCase()) ||
    camera.location?.toLowerCase().includes(search.toLowerCase())
  );

  const statusColors = {
    online: { bg: "bg-emerald-500/10", text: "text-emerald-500", border: "border-emerald-500/30", icon: Wifi },
    offline: { bg: "bg-gray-500/10", text: "text-gray-500", border: "border-gray-500/30", icon: WifiOff },
    error: { bg: "bg-red-500/10", text: "text-red-500", border: "border-red-500/30", icon: WifiOff },
    disabled: { bg: "bg-amber-500/10", text: "text-amber-500", border: "border-amber-500/30", icon: WifiOff }
  };

  return (
    <div className="p-6 space-y-6" data-testid="admin-cameras-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            CAMERA MANAGEMENT
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage RTSP cameras and detection settings across all clients
          </p>
        </div>
        
        <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
          <DialogTrigger asChild>
            <Button className="flex items-center gap-2" data-testid="add-camera-btn">
              <Plus className="w-4 h-4" />
              Add Camera
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>Add New Camera</DialogTitle>
              <DialogDescription>
                Configure a new RTSP camera for a client
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Client *</Label>
                <Select
                  value={newCamera.client_id}
                  onValueChange={(value) => setNewCamera({ ...newCamera, client_id: value })}
                >
                  <SelectTrigger data-testid="camera-client-select">
                    <SelectValue placeholder="Select client" />
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
              <div className="space-y-2">
                <Label>Camera Name *</Label>
                <Input
                  placeholder="Front Entrance Camera"
                  value={newCamera.name}
                  onChange={(e) => setNewCamera({ ...newCamera, name: e.target.value })}
                  data-testid="camera-name-input"
                />
              </div>
              <div className="space-y-2">
                <Label>Location *</Label>
                <Input
                  placeholder="Main entrance, Store #1"
                  value={newCamera.location}
                  onChange={(e) => setNewCamera({ ...newCamera, location: e.target.value })}
                  data-testid="camera-location-input"
                />
              </div>
              <div className="space-y-2">
                <Label>RTSP URL</Label>
                <Input
                  placeholder="rtsp://user:pass@192.168.1.100:554/stream1"
                  value={newCamera.rtsp_url}
                  onChange={(e) => setNewCamera({ ...newCamera, rtsp_url: e.target.value })}
                  data-testid="camera-rtsp-input"
                />
                <p className="text-xs text-muted-foreground">
                  Format: rtsp://username:password@ip:port/stream
                </p>
              </div>
              <div className="space-y-2">
                <Label>Detection Sensitivity</Label>
                <Select
                  value={newCamera.sensitivity}
                  onValueChange={(value) => setNewCamera({ ...newCamera, sensitivity: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low (fewer alerts)</SelectItem>
                    <SelectItem value="medium">Medium (balanced)</SelectItem>
                    <SelectItem value="high">High (more alerts)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-center justify-between">
                <Label>Enable Detection</Label>
                <Switch
                  checked={newCamera.detection_enabled}
                  onCheckedChange={(checked) => setNewCamera({ ...newCamera, detection_enabled: checked })}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => { setShowAddDialog(false); resetForm(); }}>
                Cancel
              </Button>
              <Button onClick={handleAddCamera} data-testid="create-camera-btn">
                Create Camera
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <div className="flex gap-4 flex-wrap">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search cameras..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
            data-testid="search-cameras-input"
          />
        </div>
        <Select value={clientFilter} onValueChange={setClientFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="All Clients" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Clients</SelectItem>
            {clients.map(client => (
              <SelectItem key={client.client_id} value={client.client_id}>
                {client.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="online">Online</SelectItem>
            <SelectItem value="offline">Offline</SelectItem>
            <SelectItem value="error">Error</SelectItem>
            <SelectItem value="disabled">Disabled</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-md bg-blue-500/10 border border-blue-500/30">
              <Camera className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{cameras.length}</p>
              <p className="text-xs text-muted-foreground">Total Cameras</p>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-md bg-emerald-500/10 border border-emerald-500/30">
              <Wifi className="w-5 h-5 text-emerald-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{cameras.filter(c => c.status === "online").length}</p>
              <p className="text-xs text-muted-foreground">Online</p>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-md bg-gray-500/10 border border-gray-500/30">
              <WifiOff className="w-5 h-5 text-gray-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{cameras.filter(c => c.status === "offline").length}</p>
              <p className="text-xs text-muted-foreground">Offline</p>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-md bg-red-500/10 border border-red-500/30">
              <Activity className="w-5 h-5 text-red-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{cameras.filter(c => c.status === "error").length}</p>
              <p className="text-xs text-muted-foreground">Errors</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Cameras Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="bg-card/50 border-white/5">
              <CardContent className="p-6">
                <div className="skeleton h-6 w-32 mb-4" />
                <div className="skeleton h-4 w-48 mb-2" />
                <div className="skeleton h-4 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
      ) : filteredCameras.length === 0 ? (
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-12 text-center">
            <Camera className="w-16 h-16 mx-auto mb-4 text-muted-foreground/30" />
            <h3 className="text-lg font-semibold mb-2">No cameras found</h3>
            <p className="text-muted-foreground mb-4">
              {search ? "Try adjusting your search" : "Add your first camera to get started"}
            </p>
            {!search && (
              <Button onClick={() => setShowAddDialog(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Add Camera
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredCameras.map((camera, idx) => {
            const colors = statusColors[camera.status] || statusColors.offline;
            const StatusIcon = colors.icon;
            return (
              <motion.div
                key={camera.camera_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
              >
                <Card className="bg-card/50 border-white/5 hover:border-white/10 transition-colors" data-testid={`camera-card-${camera.camera_id}`}>
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-md bg-cyan-500/10 border border-cyan-500/30">
                          <Camera className="w-5 h-5 text-cyan-500" />
                        </div>
                        <div>
                          <h3 className="font-semibold">{camera.name}</h3>
                          <p className="text-xs text-muted-foreground flex items-center gap-1">
                            <MapPin className="w-3 h-3" />
                            {camera.location}
                          </p>
                        </div>
                      </div>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => setEditingCamera(camera)}>
                            <Pencil className="w-4 h-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleToggleStatus(camera)}>
                            {camera.status === "online" ? (
                              <>
                                <PowerOff className="w-4 h-4 mr-2" />
                                Disable
                              </>
                            ) : (
                              <>
                                <Power className="w-4 h-4 mr-2" />
                                Enable
                              </>
                            )}
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem onClick={() => handleDeleteCamera(camera.camera_id)} className="text-red-500">
                            <Trash2 className="w-4 h-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>

                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <Badge 
                          variant="outline" 
                          className={`${colors.bg} ${colors.text} ${colors.border} uppercase text-[10px]`}
                        >
                          <StatusIcon className="w-3 h-3 mr-1" />
                          {camera.status}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {camera.detection_settings?.sensitivity || 'medium'} sensitivity
                        </span>
                      </div>

                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Building2 className="w-3 h-3" />
                        <span>{camera.client_name || 'Unknown Client'}</span>
                      </div>

                      {camera.rtsp_url && (
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <Link className="w-3 h-3" />
                          <span className="truncate">{camera.rtsp_url.replace(/\/\/.*:.*@/, '//***:***@')}</span>
                        </div>
                      )}

                      <div className="pt-2 border-t border-white/5 flex items-center justify-between">
                        <span className="text-xs text-muted-foreground">
                          Detection: {camera.detection_settings?.enabled !== false ? 'ON' : 'OFF'}
                        </span>
                        {camera.health && (
                          <span className="text-xs text-muted-foreground">
                            {camera.health.uptime_percent?.toFixed(1)}% uptime
                          </span>
                        )}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Edit Camera Dialog */}
      <Dialog open={!!editingCamera} onOpenChange={(open) => !open && setEditingCamera(null)}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit Camera</DialogTitle>
            <DialogDescription>
              Update camera configuration
            </DialogDescription>
          </DialogHeader>
          {editingCamera && (
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Camera Name</Label>
                <Input
                  value={editingCamera.name}
                  onChange={(e) => setEditingCamera({ ...editingCamera, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Location</Label>
                <Input
                  value={editingCamera.location}
                  onChange={(e) => setEditingCamera({ ...editingCamera, location: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>RTSP URL</Label>
                <Input
                  value={editingCamera.rtsp_url || ""}
                  onChange={(e) => setEditingCamera({ ...editingCamera, rtsp_url: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Detection Sensitivity</Label>
                <Select
                  value={editingCamera.detection_settings?.sensitivity || "medium"}
                  onValueChange={(value) => setEditingCamera({ 
                    ...editingCamera, 
                    detection_settings: { ...editingCamera.detection_settings, sensitivity: value }
                  })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingCamera(null)}>
              Cancel
            </Button>
            <Button onClick={handleUpdateCamera}>
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
