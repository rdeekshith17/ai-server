import { useState, useEffect } from "react";
import axios from "axios";
import { 
  Users, 
  Plus, 
  Search,
  MoreHorizontal,
  Pencil,
  Trash2,
  Building2,
  Shield,
  UserCog,
  Eye,
  Mail,
  Clock
} from "lucide-react";
import { Card, CardContent } from "../../components/ui/card";
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
import { Avatar, AvatarFallback, AvatarImage } from "../../components/ui/avatar";
import { toast } from "sonner";
import { motion } from "framer-motion";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const ROLES = [
  { value: "super_admin", label: "Super Admin", color: "text-red-500", bg: "bg-red-500/10", border: "border-red-500/30" },
  { value: "client_owner", label: "Client Owner", color: "text-purple-500", bg: "bg-purple-500/10", border: "border-purple-500/30" },
  { value: "client_staff", label: "Client Staff", color: "text-blue-500", bg: "bg-blue-500/10", border: "border-blue-500/30" },
  { value: "client_viewer", label: "Client Viewer", color: "text-gray-500", bg: "bg-gray-500/10", border: "border-gray-500/30" },
];

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState("all");
  const [clientFilter, setClientFilter] = useState("all");
  const [assigningUser, setAssigningUser] = useState(null);
  const [assignment, setAssignment] = useState({ client_id: "", role: "client_viewer" });

  useEffect(() => {
    fetchUsers();
    fetchClients();
  }, [roleFilter, clientFilter]);

  const fetchUsers = async () => {
    try {
      const params = new URLSearchParams();
      if (roleFilter && roleFilter !== "all") params.append("role", roleFilter);
      if (clientFilter && clientFilter !== "all") params.append("client_id", clientFilter);
      
      const response = await axios.get(`${API}/admin/users?${params}`, { withCredentials: true });
      setUsers(response.data.users || []);
    } catch (error) {
      console.error("Failed to fetch users:", error);
      toast.error("Failed to load users");
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

  const handleAssignUser = async () => {
    try {
      if (!assignment.client_id || !assignment.role) {
        toast.error("Please select client and role");
        return;
      }

      await axios.put(
        `${API}/admin/users/${assigningUser.user_id}/assign`,
        {
          email: assigningUser.email,
          client_id: assignment.client_id,
          role: assignment.role
        },
        { withCredentials: true }
      );
      
      toast.success("User assigned successfully");
      setAssigningUser(null);
      setAssignment({ client_id: "", role: "client_viewer" });
      fetchUsers();
    } catch (error) {
      toast.error(error.response?.data?.detail || "Failed to assign user");
    }
  };

  const handleUpdateRole = async (userId, newRole) => {
    try {
      await axios.put(
        `${API}/admin/users/${userId}/role?role=${newRole}`,
        {},
        { withCredentials: true }
      );
      toast.success("Role updated successfully");
      fetchUsers();
    } catch (error) {
      toast.error("Failed to update role");
    }
  };

  const filteredUsers = users.filter(user => 
    user.name?.toLowerCase().includes(search.toLowerCase()) ||
    user.email?.toLowerCase().includes(search.toLowerCase())
  );

  const getInitials = (name) => {
    if (!name) return "U";
    return name.split(" ").map(n => n[0]).join("").toUpperCase().slice(0, 2);
  };

  const getRoleInfo = (role) => {
    return ROLES.find(r => r.value === role) || ROLES[3];
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return "Never";
    const date = new Date(dateStr);
    return date.toLocaleDateString() + " " + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  return (
    <div className="p-6 space-y-6" data-testid="admin-users-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            USER MANAGEMENT
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage users and assign them to clients with appropriate roles
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-4 flex-wrap">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search users..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-10"
            data-testid="search-users-input"
          />
        </div>
        <Select value={roleFilter} onValueChange={setRoleFilter}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="All Roles" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Roles</SelectItem>
            {ROLES.map(role => (
              <SelectItem key={role.value} value={role.value}>
                {role.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={clientFilter} onValueChange={setClientFilter}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="All Clients" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Clients</SelectItem>
            <SelectItem value="unassigned">Unassigned</SelectItem>
            {clients.map(client => (
              <SelectItem key={client.client_id} value={client.client_id}>
                {client.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-md bg-blue-500/10 border border-blue-500/30">
              <Users className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{users.length}</p>
              <p className="text-xs text-muted-foreground">Total Users</p>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-md bg-red-500/10 border border-red-500/30">
              <Shield className="w-5 h-5 text-red-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{users.filter(u => u.role === "super_admin").length}</p>
              <p className="text-xs text-muted-foreground">Admins</p>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-md bg-purple-500/10 border border-purple-500/30">
              <UserCog className="w-5 h-5 text-purple-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{users.filter(u => u.role === "client_owner").length}</p>
              <p className="text-xs text-muted-foreground">Client Owners</p>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-md bg-gray-500/10 border border-gray-500/30">
              <Eye className="w-5 h-5 text-gray-500" />
            </div>
            <div>
              <p className="text-2xl font-bold">{users.filter(u => !u.client_id).length}</p>
              <p className="text-xs text-muted-foreground">Unassigned</p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Users Table */}
      {loading ? (
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-6">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="flex items-center gap-4 py-4 border-b border-white/5">
                <div className="skeleton h-10 w-10 rounded-full" />
                <div className="flex-1">
                  <div className="skeleton h-4 w-32 mb-2" />
                  <div className="skeleton h-3 w-48" />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      ) : filteredUsers.length === 0 ? (
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-12 text-center">
            <Users className="w-16 h-16 mx-auto mb-4 text-muted-foreground/30" />
            <h3 className="text-lg font-semibold mb-2">No users found</h3>
            <p className="text-muted-foreground">
              {search ? "Try adjusting your search" : "Users will appear here after they sign in"}
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-0">
            <div className="divide-y divide-white/5">
              {filteredUsers.map((user, idx) => {
                const roleInfo = getRoleInfo(user.role);
                return (
                  <motion.div
                    key={user.user_id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: idx * 0.03 }}
                    className="flex items-center gap-4 p-4 hover:bg-white/[0.02] transition-colors"
                    data-testid={`user-row-${user.user_id}`}
                  >
                    <Avatar className="h-10 w-10">
                      <AvatarImage src={user.picture} alt={user.name} />
                      <AvatarFallback className="bg-blue-600/20 text-blue-400">
                        {getInitials(user.name)}
                      </AvatarFallback>
                    </Avatar>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-medium truncate">{user.name}</p>
                        <Badge 
                          variant="outline" 
                          className={`${roleInfo.bg} ${roleInfo.color} ${roleInfo.border} text-[10px] uppercase`}
                        >
                          {roleInfo.label}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Mail className="w-3 h-3" />
                          {user.email}
                        </span>
                        {user.client_name && (
                          <span className="flex items-center gap-1">
                            <Building2 className="w-3 h-3" />
                            {user.client_name}
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="text-right text-xs text-muted-foreground hidden md:block">
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        Last login: {formatDate(user.last_login_at)}
                      </div>
                    </div>

                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                          <MoreHorizontal className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => {
                          setAssigningUser(user);
                          setAssignment({ 
                            client_id: user.client_id || "", 
                            role: user.role || "client_viewer" 
                          });
                        }}>
                          <Building2 className="w-4 h-4 mr-2" />
                          Assign to Client
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem onClick={() => handleUpdateRole(user.user_id, "client_owner")}>
                          <UserCog className="w-4 h-4 mr-2" />
                          Make Owner
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleUpdateRole(user.user_id, "client_staff")}>
                          <Users className="w-4 h-4 mr-2" />
                          Make Staff
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleUpdateRole(user.user_id, "client_viewer")}>
                          <Eye className="w-4 h-4 mr-2" />
                          Make Viewer
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </motion.div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Assign User Dialog */}
      <Dialog open={!!assigningUser} onOpenChange={(open) => !open && setAssigningUser(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Assign User to Client</DialogTitle>
            <DialogDescription>
              {assigningUser && `Assign ${assigningUser.name} to a client organization`}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Client Organization</Label>
              <Select
                value={assignment.client_id}
                onValueChange={(value) => setAssignment({ ...assignment, client_id: value })}
              >
                <SelectTrigger>
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
              <Label>Role</Label>
              <Select
                value={assignment.role}
                onValueChange={(value) => setAssignment({ ...assignment, role: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="client_owner">Client Owner (full access)</SelectItem>
                  <SelectItem value="client_staff">Client Staff (view + acknowledge)</SelectItem>
                  <SelectItem value="client_viewer">Client Viewer (view only)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAssigningUser(null)}>
              Cancel
            </Button>
            <Button onClick={handleAssignUser}>
              Assign User
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
