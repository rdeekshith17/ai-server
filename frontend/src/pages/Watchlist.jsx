import { useState, useEffect, useCallback } from "react";
import axios from "axios";
import { 
  UserPlus, 
  Users, 
  Trash2, 
  AlertTriangle,
  Shield,
  Eye,
  Camera,
  Upload,
  X
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { ScrollArea } from "../components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../components/ui/dialog";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const threatColors = {
  high: { bg: "bg-red-500/10", text: "text-red-500", border: "border-red-500/30" },
  medium: { bg: "bg-amber-500/10", text: "text-amber-500", border: "border-amber-500/30" },
  low: { bg: "bg-blue-500/10", text: "text-blue-500", border: "border-blue-500/30" }
};

export default function Watchlist() {
  const [watchlist, setWatchlist] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [selectedPerson, setSelectedPerson] = useState(null);
  const [uploading, setUploading] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    name: "",
    alias: "",
    description: "",
    threat_level: "high",
    notes: "",
    photo: null
  });
  const [photoPreview, setPhotoPreview] = useState(null);

  useEffect(() => {
    fetchWatchlist();
    fetchStats();
  }, []);

  const fetchWatchlist = async () => {
    try {
      const response = await axios.get(`${API}/watchlist`);
      setWatchlist(response.data.watchlist || []);
    } catch (err) {
      console.error("Failed to fetch watchlist:", err);
      toast.error("Failed to load watchlist");
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API}/watchlist/stats/summary`);
      setStats(response.data);
    } catch (err) {
      console.error("Failed to fetch stats:", err);
    }
  };

  const handlePhotoChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        toast.error("Please select an image file");
        return;
      }
      setFormData({ ...formData, photo: file });
      const reader = new FileReader();
      reader.onloadend = () => setPhotoPreview(reader.result);
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name || !formData.photo) {
      toast.error("Name and photo are required");
      return;
    }

    setUploading(true);
    try {
      const data = new FormData();
      data.append("name", formData.name);
      data.append("photo", formData.photo);
      if (formData.alias) data.append("alias", formData.alias);
      if (formData.description) data.append("description", formData.description);
      data.append("threat_level", formData.threat_level);
      if (formData.notes) data.append("notes", formData.notes);

      await axios.post(`${API}/watchlist`, data, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      toast.success("Person added to watchlist");
      setShowAddDialog(false);
      resetForm();
      fetchWatchlist();
      fetchStats();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to add person");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (personId) => {
    try {
      await axios.delete(`${API}/watchlist/${personId}`);
      setWatchlist(watchlist.filter(p => p.id !== personId));
      toast.success("Person removed from watchlist");
      fetchStats();
    } catch (err) {
      toast.error("Failed to remove person");
    }
  };

  const resetForm = () => {
    setFormData({
      name: "",
      alias: "",
      description: "",
      threat_level: "high",
      notes: "",
      photo: null
    });
    setPhotoPreview(null);
  };

  const viewPerson = async (personId) => {
    try {
      const response = await axios.get(`${API}/watchlist/${personId}`);
      setSelectedPerson(response.data);
    } catch (err) {
      toast.error("Failed to load person details");
    }
  };

  return (
    <div className="p-6 space-y-6" data-testid="watchlist-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            WATCHLIST
          </h1>
          <p className="text-muted-foreground mt-1">
            Known shoplifters - Alert when detected in store
          </p>
        </div>
        <button
          onClick={() => setShowAddDialog(true)}
          className="btn-primary flex items-center gap-2"
          data-testid="add-person-btn"
        >
          <UserPlus className="w-4 h-4" />
          Add Person
        </button>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-card/50 border-white/5">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-md bg-blue-500/10 border border-blue-500/30">
                <Users className="w-6 h-6 text-blue-500" />
              </div>
              <div>
                <p className="text-2xl font-bold" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                  {stats.total}
                </p>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">
                  Total People
                </p>
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-card/50 border-white/5">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-md bg-red-500/10 border border-red-500/30">
                <AlertTriangle className="w-6 h-6 text-red-500" />
              </div>
              <div>
                <p className="text-2xl font-bold text-red-500" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                  {stats.by_threat_level?.high || 0}
                </p>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">
                  High Threat
                </p>
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-card/50 border-white/5">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-md bg-amber-500/10 border border-amber-500/30">
                <Shield className="w-6 h-6 text-amber-500" />
              </div>
              <div>
                <p className="text-2xl font-bold text-amber-500" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                  {stats.by_threat_level?.medium || 0}
                </p>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">
                  Medium Threat
                </p>
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-card/50 border-white/5">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="p-3 rounded-md bg-emerald-500/10 border border-emerald-500/30">
                <Shield className="w-6 h-6 text-emerald-500" />
              </div>
              <div>
                <p className="text-2xl font-bold text-emerald-500" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                  {stats.active}
                </p>
                <p className="text-xs text-muted-foreground uppercase tracking-wider">
                  Active Alerts
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Live Camera Feed Placeholder */}
      <Card className="bg-card/50 border-white/5 border-dashed">
        <CardContent className="p-6">
          <div className="flex items-center gap-4">
            <div className="p-4 rounded-md bg-cyan-500/10 border border-cyan-500/30">
              <Camera className="w-8 h-8 text-cyan-400" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                LIVE CAMERA FEED
              </h3>
              <p className="text-sm text-muted-foreground">
                Connect RTSP camera streams for real-time monitoring and automatic watchlist alerts
              </p>
              <p className="text-xs text-cyan-400 mt-2">
                Coming soon - Add your camera RTSP URLs here
              </p>
            </div>
            <button 
              className="px-4 py-2 rounded-sm bg-secondary border border-white/10 text-muted-foreground cursor-not-allowed"
              disabled
            >
              Configure Cameras
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Watchlist Grid */}
      <Card className="bg-card/50 border-white/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            <Users className="w-5 h-5 text-blue-500" />
            WATCHLIST ({watchlist.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="skeleton h-32 rounded-lg" />
              ))}
            </div>
          ) : watchlist.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <AnimatePresence>
                {watchlist.map((person, idx) => {
                  const colors = threatColors[person.threat_level] || threatColors.medium;
                  return (
                    <motion.div
                      key={person.id}
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ delay: idx * 0.05 }}
                      className={`p-4 rounded-lg border ${colors.border} ${colors.bg} hover:border-white/20 transition-colors`}
                      data-testid={`watchlist-person-${person.id}`}
                    >
                      <div className="flex items-start gap-3">
                        <div className="w-16 h-16 rounded-md bg-secondary flex items-center justify-center overflow-hidden">
                          {person.has_photo ? (
                            <div className="w-full h-full bg-gradient-to-br from-gray-700 to-gray-800 flex items-center justify-center">
                              <Users className="w-8 h-8 text-gray-500" />
                            </div>
                          ) : (
                            <Users className="w-8 h-8 text-muted-foreground" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <h4 className="font-medium truncate">{person.name}</h4>
                            <Badge className={`${colors.bg} ${colors.text} ${colors.border} text-[10px] uppercase`}>
                              {person.threat_level}
                            </Badge>
                          </div>
                          {person.alias && (
                            <p className="text-xs text-muted-foreground">
                              AKA: {person.alias}
                            </p>
                          )}
                          {person.description && (
                            <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                              {person.description}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center gap-2 mt-3 pt-3 border-t border-white/5">
                        <button
                          onClick={() => viewPerson(person.id)}
                          className="flex-1 flex items-center justify-center gap-1 py-1.5 rounded-sm bg-white/5 hover:bg-white/10 text-xs transition-colors"
                        >
                          <Eye className="w-3 h-3" />
                          View
                        </button>
                        <button
                          onClick={() => handleDelete(person.id)}
                          className="flex items-center justify-center gap-1 py-1.5 px-3 rounded-sm bg-red-500/10 hover:bg-red-500/20 text-red-500 text-xs transition-colors"
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          ) : (
            <div className="text-center py-12">
              <Users className="w-16 h-16 text-muted-foreground/30 mx-auto mb-4" />
              <p className="text-lg font-medium">No people in watchlist</p>
              <p className="text-sm text-muted-foreground mt-1">
                Add known shoplifters to receive alerts when they enter your store
              </p>
              <button
                onClick={() => setShowAddDialog(true)}
                className="btn-primary mt-4"
              >
                <UserPlus className="w-4 h-4 mr-2 inline" />
                Add First Person
              </button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add Person Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="max-w-md bg-card border-white/10">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Rajdhani, sans-serif' }}>
              ADD TO WATCHLIST
            </DialogTitle>
            <DialogDescription>
              Upload a photo and details of a known shoplifter
            </DialogDescription>
          </DialogHeader>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Photo Upload */}
            <div>
              <Label className="text-sm text-muted-foreground">Photo *</Label>
              <div 
                className={`mt-2 border-2 border-dashed rounded-lg p-4 text-center cursor-pointer transition-colors ${
                  photoPreview ? 'border-blue-500/50' : 'border-white/10 hover:border-white/20'
                }`}
                onClick={() => document.getElementById('photo-input').click()}
              >
                <input
                  id="photo-input"
                  type="file"
                  accept="image/*"
                  onChange={handlePhotoChange}
                  className="hidden"
                />
                {photoPreview ? (
                  <div className="relative">
                    <img 
                      src={photoPreview} 
                      alt="Preview" 
                      className="w-32 h-32 object-cover rounded-md mx-auto"
                    />
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setPhotoPreview(null);
                        setFormData({ ...formData, photo: null });
                      }}
                      className="absolute top-0 right-0 p-1 bg-red-500 rounded-full transform translate-x-1/2 -translate-y-1/2"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ) : (
                  <div>
                    <Upload className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                    <p className="text-sm text-muted-foreground">
                      Click to upload photo
                    </p>
                  </div>
                )}
              </div>
            </div>

            {/* Name */}
            <div>
              <Label htmlFor="name" className="text-sm text-muted-foreground">Name *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Full name"
                className="mt-1 bg-secondary border-white/10"
                required
              />
            </div>

            {/* Alias */}
            <div>
              <Label htmlFor="alias" className="text-sm text-muted-foreground">Alias / Nickname</Label>
              <Input
                id="alias"
                value={formData.alias}
                onChange={(e) => setFormData({ ...formData, alias: e.target.value })}
                placeholder="Known aliases"
                className="mt-1 bg-secondary border-white/10"
              />
            </div>

            {/* Threat Level */}
            <div>
              <Label className="text-sm text-muted-foreground">Threat Level</Label>
              <Select 
                value={formData.threat_level} 
                onValueChange={(v) => setFormData({ ...formData, threat_level: v })}
              >
                <SelectTrigger className="mt-1 bg-secondary border-white/10">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="high">High - Repeat offender</SelectItem>
                  <SelectItem value="medium">Medium - Known shoplifter</SelectItem>
                  <SelectItem value="low">Low - Suspected</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Description */}
            <div>
              <Label htmlFor="description" className="text-sm text-muted-foreground">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="Physical description, distinguishing features..."
                className="mt-1 bg-secondary border-white/10 h-20"
              />
            </div>

            {/* Notes */}
            <div>
              <Label htmlFor="notes" className="text-sm text-muted-foreground">Notes</Label>
              <Textarea
                id="notes"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                placeholder="Previous incidents, behavior patterns..."
                className="mt-1 bg-secondary border-white/10 h-20"
              />
            </div>

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={() => { setShowAddDialog(false); resetForm(); }}
                className="flex-1 py-2 rounded-sm bg-secondary border border-white/10 hover:bg-secondary/80"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={uploading || !formData.name || !formData.photo}
                className="flex-1 btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {uploading ? "Adding..." : "Add to Watchlist"}
              </button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* View Person Dialog */}
      <Dialog open={!!selectedPerson} onOpenChange={() => setSelectedPerson(null)}>
        <DialogContent className="max-w-md bg-card border-white/10">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Rajdhani, sans-serif' }}>
              PERSON DETAILS
            </DialogTitle>
          </DialogHeader>
          
          {selectedPerson && (
            <div className="space-y-4">
              {/* Photo */}
              {selectedPerson.photo_base64 && (
                <div className="flex justify-center">
                  <img 
                    src={`data:image/jpeg;base64,${selectedPerson.photo_base64}`}
                    alt={selectedPerson.name}
                    className="w-40 h-40 object-cover rounded-lg border border-white/10"
                  />
                </div>
              )}
              
              <div className="text-center">
                <h3 className="text-xl font-bold">{selectedPerson.name}</h3>
                {selectedPerson.alias && (
                  <p className="text-sm text-muted-foreground">AKA: {selectedPerson.alias}</p>
                )}
                <Badge className={`mt-2 ${
                  threatColors[selectedPerson.threat_level]?.bg
                } ${threatColors[selectedPerson.threat_level]?.text} ${
                  threatColors[selectedPerson.threat_level]?.border
                } uppercase`}>
                  {selectedPerson.threat_level} Threat
                </Badge>
              </div>

              {selectedPerson.description && (
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Description</p>
                  <p className="text-sm">{selectedPerson.description}</p>
                </div>
              )}

              {selectedPerson.notes && (
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">Notes</p>
                  <p className="text-sm">{selectedPerson.notes}</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-white/5">
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Added</p>
                  <p className="text-sm font-mono">
                    {new Date(selectedPerson.added_at).toLocaleDateString()}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Status</p>
                  <p className={`text-sm ${selectedPerson.is_active ? 'text-emerald-500' : 'text-muted-foreground'}`}>
                    {selectedPerson.is_active ? 'Active' : 'Inactive'}
                  </p>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
