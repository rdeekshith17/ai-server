import { useState, useEffect } from "react";
import axios from "axios";
import { 
  Building2, 
  Plus, 
  Search,
  MoreHorizontal,
  Pencil,
  Trash2,
  Power,
  PowerOff,
  Camera,
  Users,
  AlertTriangle,
  RefreshCw,
  X
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
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

// Get auth headers
const getAuthHeaders = () => {
  const token = localStorage.getItem("session_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const PLANS = [
  { value: "trial", label: "Trial (14 days)", cameras: 2, users: 1 },
  { value: "starter", label: "Starter ($99/mo)", cameras: 4, users: 2 },
  { value: "professional", label: "Professional ($299/mo)", cameras: 16, users: 5 },
  { value: "enterprise", label: "Enterprise ($799/mo)", cameras: 64, users: "Unlimited" },
];

const STATUSES = [
  { value: "active", label: "Active" },
  { value: "trial", label: "Trial" },
  { value: "suspended", label: "Suspended" },
  { value: "cancelled", label: "Cancelled" },
];

export default function AdminClients() {
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  
  // Add dialog
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [newClient, setNewClient] = useState({
    name: "",
    slug: "",
    contact_name: "",
    contact_email: "",
    contact_phone: "",
    plan: "trial"
  });
  
  // Edit dialog
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [editingClient, setEditingClient] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchClients();
  }, [statusFilter]);

  const fetchClients = async () => {
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append("status", statusFilter);
      
      const response = await axios.get(`${API}/admin/clients?${params}`, { 
        withCredentials: true,
        headers: getAuthHeaders()
      });
      setClients(response.data.clients || []);
    } catch (error) {
      console.error("Failed to fetch clients:", error);
      toast.error("Failed to load clients");
    } finally {
      setLoading(false);
    }
  };

  const handleAddClient = async () => {
    try {
      if (!newClient.name || !newClient.contact_email) {
        toast.error("Please fill in required fields (name, email)");
        return;
      }

      setSaving(true);
      const response = await axios.post(`${API}/admin/clients`, newClient, { 
        withCredentials: true,
        headers: getAuthHeaders()
      });
      
      if (response.data.success) {
        toast.success("Client created successfully");
        setShowAddDialog(false);
        setNewClient({
          name: "",
          slug: "",
          contact_name: "",
          contact_email: "",
          contact_phone: "",
          plan: "trial"
        });
        fetchClients();
      }
    } catch (error) {
      console.error("Failed to create client:", error);
      toast.error(error.response?.data?.detail || "Failed to create client");
    } finally {
      setSaving(false);
    }
  };

  const handleEditClient = (client) => {
    setEditingClient({
      client_id: client.client_id,
      name: client.name,
      contact_name: client.contact?.name || "",
      contact_email: client.contact?.email || "",
      contact_phone: client.contact?.phone || "",
      status: client.status,
      plan: client.subscription?.plan || "trial"
    });
    setShowEditDialog(true);
  };

  const handleSaveEdit = async () => {
    if (!editingClient) return;
    
    try {
      setSaving(true);
      const response = await axios.put(
        `${API}/admin/clients/${editingClient.client_id}`,
        {
          name: editingClient.name,
          contact_name: editingClient.contact_name,
          contact_email: editingClient.contact_email,
          contact_phone: editingClient.contact_phone,
          status: editingClient.status,
          plan: editingClient.plan
        },
        { 
          withCredentials: true,
          headers: getAuthHeaders()
        }
      );
      
      if (response.data.success) {
        toast.success("Client updated successfully");
        setShowEditDialog(false);
        setEditingClient(null);
        fetchClients();
      }
    } catch (error) {
      console.error("Failed to update client:", error);
      toast.error(error.response?.data?.detail || "Failed to update client");
    } finally {
      setSaving(false);
    }
  };

  const handleSuspend = async (clientId) => {
    try {
      await axios.post(`${API}/admin/clients/${clientId}/suspend`, {}, { 
        withCredentials: true,
        headers: getAuthHeaders()
      });
      toast.success("Client suspended");
      fetchClients();
    } catch (error) {
      toast.error("Failed to suspend client");
    }
  };

  const handleActivate = async (clientId) => {
    try {
      await axios.post(`${API}/admin/clients/${clientId}/activate`, {}, { 
        withCredentials: true,
        headers: getAuthHeaders()
      });
      toast.success("Client activated");
      fetchClients();
    } catch (error) {
      toast.error("Failed to activate client");
    }
  };

  const handleDelete = async (clientId) => {
    if (!window.confirm("Are you sure? This will delete all client data including cameras, users, and incidents.")) return;
    
    try {
      await axios.delete(`${API}/admin/clients/${clientId}`, { 
        withCredentials: true,
        headers: getAuthHeaders()
      });
      toast.success("Client deleted");
      fetchClients();
    } catch (error) {
      toast.error("Failed to delete client");
    }
  };

  const generateSlug = (name) => {
    return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
  };

  const filteredClients = clients.filter(client => 
    client.name.toLowerCase().includes(search.toLowerCase()) ||
    client.contact?.email?.toLowerCase().includes(search.toLowerCase())
  );

  const statusColors = {
    active: { bg: "bg-emerald-500/10", text: "text-emerald-500", border: "border-emerald-500/30" },
    trial: { bg: "bg-cyan-500/10", text: "text-cyan-500", border: "border-cyan-500/30" },
    suspended: { bg: "bg-red-500/10", text: "text-red-500", border: "border-red-500/30" },
    cancelled: { bg: "bg-gray-500/10", text: "text-gray-500", border: "border-gray-500/30" }
  };

  return (
    <div className="p-6 space-y-6" data-testid="admin-clients-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            CLIENT MANAGEMENT
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage your platform clients and subscriptions
          </p>
        </div>
        
        <Button onClick={() => setShowAddDialog(true)} className="flex items-center gap-2" data-testid="add-client-btn">
          <Plus className="w-4 h-4" />
          Add Client
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search clients..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
            data-testid="search-clients-input"
          />
        </div>
        <Select value={statusFilter || "all"} onValueChange={(v) => setStatusFilter(v === "all" ? "" : v)}>
          <SelectTrigger className="w-40" data-testid="status-filter-select">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="trial">Trial</SelectItem>
            <SelectItem value="suspended">Suspended</SelectItem>
            <SelectItem value="cancelled">Cancelled</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Clients Grid */}
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
      ) : filteredClients.length === 0 ? (
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-12 text-center">
            <Building2 className="w-16 h-16 mx-auto mb-4 text-muted-foreground/30" />
            <h3 className="text-lg font-semibold mb-2">No clients found</h3>
            <p className="text-muted-foreground mb-4">
              {search ? "Try adjusting your search" : "Add your first client to get started"}
            </p>
            {!search && (
              <Button onClick={() => setShowAddDialog(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Add Client
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredClients.map((client, idx) => {
            const colors = statusColors[client.status] || statusColors.active;
            return (
              <motion.div
                key={client.client_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
              >
                <Card className="bg-card/50 border-white/5 hover:border-white/10 transition-colors" data-testid={`client-card-${client.client_id}`}>
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-md bg-blue-500/10 border border-blue-500/30">
                          <Building2 className="w-5 h-5 text-blue-500" />
                        </div>
                        <div>
                          <h3 className="font-semibold">{client.name}</h3>
                          <p className="text-xs text-muted-foreground">{client.slug}</p>
                        </div>
                      </div>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleEditClient(client)}>
                            <Pencil className="w-4 h-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          {client.status === "active" || client.status === "trial" ? (
                            <DropdownMenuItem onClick={() => handleSuspend(client.client_id)} className="text-amber-500">
                              <PowerOff className="w-4 h-4 mr-2" />
                              Suspend
                            </DropdownMenuItem>
                          ) : (
                            <DropdownMenuItem onClick={() => handleActivate(client.client_id)} className="text-emerald-500">
                              <Power className="w-4 h-4 mr-2" />
                              Activate
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem onClick={() => handleDelete(client.client_id)} className="text-red-500">
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
                          {client.status}
                        </Badge>
                        <span className="text-xs text-muted-foreground capitalize">
                          {client.subscription?.plan || 'trial'} plan
                        </span>
                      </div>

                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <Camera className="w-4 h-4" />
                          <span>{client.cameras_count || 0}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <Users className="w-4 h-4" />
                          <span>{client.users_count || 0}</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <AlertTriangle className="w-4 h-4" />
                          <span>{client.incidents_24h || 0}</span>
                        </div>
                      </div>

                      <div className="pt-2 border-t border-white/5">
                        <p className="text-xs text-muted-foreground">{client.contact?.email}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>
      )}

      {/* Add Client Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Rajdhani, sans-serif' }}>ADD NEW CLIENT</DialogTitle>
            <DialogDescription>
              Create a new client account for your platform
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Company Name *</Label>
              <Input
                placeholder="ABC Liquor Store"
                value={newClient.name}
                onChange={(e) => {
                  setNewClient({ 
                    ...newClient, 
                    name: e.target.value,
                    slug: generateSlug(e.target.value)
                  });
                }}
                data-testid="client-name-input"
              />
            </div>
            <div className="space-y-2">
              <Label>Contact Name</Label>
              <Input
                placeholder="John Smith"
                value={newClient.contact_name}
                onChange={(e) => setNewClient({ ...newClient, contact_name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Contact Email *</Label>
              <Input
                type="email"
                placeholder="john@company.com"
                value={newClient.contact_email}
                onChange={(e) => setNewClient({ ...newClient, contact_email: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Contact Phone</Label>
              <Input
                placeholder="+1 555-0123"
                value={newClient.contact_phone}
                onChange={(e) => setNewClient({ ...newClient, contact_phone: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Subscription Plan</Label>
              <Select
                value={newClient.plan}
                onValueChange={(value) => setNewClient({ ...newClient, plan: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PLANS.map(plan => (
                    <SelectItem key={plan.value} value={plan.value}>
                      {plan.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowAddDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleAddClient} disabled={saving}>
              {saving ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Plus className="w-4 h-4 mr-2" />}
              Create Client
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Client Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Rajdhani, sans-serif' }}>EDIT CLIENT</DialogTitle>
            <DialogDescription>
              Update client details
            </DialogDescription>
          </DialogHeader>
          {editingClient && (
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Company Name *</Label>
                <Input
                  value={editingClient.name}
                  onChange={(e) => setEditingClient({ ...editingClient, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Contact Name</Label>
                <Input
                  value={editingClient.contact_name}
                  onChange={(e) => setEditingClient({ ...editingClient, contact_name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Contact Email</Label>
                <Input
                  type="email"
                  value={editingClient.contact_email}
                  onChange={(e) => setEditingClient({ ...editingClient, contact_email: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label>Contact Phone</Label>
                <Input
                  value={editingClient.contact_phone}
                  onChange={(e) => setEditingClient({ ...editingClient, contact_phone: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Status</Label>
                  <Select
                    value={editingClient.status}
                    onValueChange={(value) => setEditingClient({ ...editingClient, status: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {STATUSES.map(status => (
                        <SelectItem key={status.value} value={status.value}>
                          {status.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Plan</Label>
                  <Select
                    value={editingClient.plan}
                    onValueChange={(value) => setEditingClient({ ...editingClient, plan: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {PLANS.map(plan => (
                        <SelectItem key={plan.value} value={plan.value}>
                          {plan.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
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
    </div>
  );
}
