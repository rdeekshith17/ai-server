import { useState, useEffect } from "react";
import axios from "axios";
import { 
  AlertTriangle, 
  Filter, 
  Trash2, 
  ShieldCheck,
  Search,
  Eye,
  ChevronDown,
  Image,
  User,
  Package,
  ArrowRight,
  DollarSign
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { ScrollArea } from "../components/ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const severityConfig = {
  critical: { 
    bg: "bg-red-500/10", 
    text: "text-red-500", 
    border: "border-red-500/30",
    icon: "text-red-500"
  },
  warning: { 
    bg: "bg-amber-500/10", 
    text: "text-amber-500", 
    border: "border-amber-500/30",
    icon: "text-amber-500"
  },
  safe: { 
    bg: "bg-emerald-500/10", 
    text: "text-emerald-500", 
    border: "border-emerald-500/30",
    icon: "text-emerald-500"
  }
};

const concealmentIcons = {
  bag: "🛍️",
  coat: "🧥",
  body: "👤",
  none: "✓"
};

export default function Incidents() {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [storeFilter, setStoreFilter] = useState("all");
  const [selectedIncident, setSelectedIncident] = useState(null);
  const [incidentImage, setIncidentImage] = useState(null);
  const [loadingImage, setLoadingImage] = useState(false);

  useEffect(() => {
    fetchIncidents();
  }, [severityFilter, storeFilter]);

  const fetchIncidents = async () => {
    try {
      const params = new URLSearchParams();
      if (severityFilter !== "all") params.append("severity", severityFilter);
      if (storeFilter !== "all") params.append("store_type", storeFilter);
      
      const response = await axios.get(`${API}/incidents?${params.toString()}`);
      setIncidents(response.data.incidents || []);
    } catch (err) {
      console.error("Failed to fetch incidents:", err);
      toast.error("Failed to load incidents");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (incidentId) => {
    try {
      await axios.delete(`${API}/incidents/${incidentId}`);
      setIncidents(incidents.filter(i => i.id !== incidentId));
      toast.success("Incident deleted");
    } catch (err) {
      toast.error("Failed to delete incident");
    }
  };

  const viewIncidentDetails = async (incidentId) => {
    setLoadingImage(true);
    try {
      const response = await axios.get(`${API}/incidents/${incidentId}`);
      setSelectedIncident(response.data);
      setIncidentImage(response.data.frame_image || null);
    } catch (err) {
      toast.error("Failed to load incident details");
    } finally {
      setLoadingImage(false);
    }
  };

  const filteredIncidents = incidents.filter(incident => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      incident.description?.toLowerCase().includes(query) ||
      incident.video_name?.toLowerCase().includes(query) ||
      incident.behaviors_detected?.some(b => b.toLowerCase().includes(query)) ||
      incident.items_involved?.some(i => i.toLowerCase().includes(query)) ||
      incident.person_description?.toLowerCase().includes(query)
    );
  });

  const formatDate = (dateStr) => {
    if (!dateStr) return "Unknown";
    const date = new Date(dateStr);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    });
  };

  return (
    <div className="p-6 space-y-6" data-testid="incidents-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            INCIDENT LOG
          </h1>
          <p className="text-muted-foreground mt-1">
            View detected theft incidents with evidence images
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/30">
            {incidents.filter(i => i.severity === "critical").length} Critical
          </Badge>
          <Badge variant="outline" className="bg-amber-500/10 text-amber-500 border-amber-500/30">
            {incidents.filter(i => i.severity === "warning").length} Warnings
          </Badge>
        </div>
      </div>

      {/* Filters */}
      <Card className="bg-card/50 border-white/5">
        <CardContent className="p-4">
          <div className="flex flex-wrap gap-4 items-center">
            {/* Search */}
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search incidents, items, descriptions..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 bg-secondary border-white/10"
                data-testid="search-input"
              />
            </div>

            {/* Severity Filter */}
            <Select value={severityFilter} onValueChange={setSeverityFilter}>
              <SelectTrigger className="w-[160px] bg-secondary border-white/10" data-testid="severity-filter">
                <Filter className="w-4 h-4 mr-2 text-muted-foreground" />
                <SelectValue placeholder="Severity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Severities</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="warning">Warning</SelectItem>
                <SelectItem value="safe">Safe</SelectItem>
              </SelectContent>
            </Select>

            {/* Store Filter */}
            <Select value={storeFilter} onValueChange={setStoreFilter}>
              <SelectTrigger className="w-[180px] bg-secondary border-white/10" data-testid="store-filter">
                <SelectValue placeholder="Store Type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Stores</SelectItem>
                <SelectItem value="convenience">Convenience</SelectItem>
                <SelectItem value="liquor">Liquor Store</SelectItem>
                <SelectItem value="gas_station">Gas Station</SelectItem>
                <SelectItem value="retail">Retail</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Incidents Grid */}
      <Card className="bg-card/50 border-white/5">
        <CardHeader className="pb-0">
          <CardTitle className="flex items-center gap-2" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            INCIDENTS ({filteredIncidents.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 mt-4">
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="skeleton h-64 rounded-lg" />
              ))}
            </div>
          ) : filteredIncidents.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <AnimatePresence>
                {filteredIncidents.map((incident, idx) => {
                  const config = severityConfig[incident.severity] || severityConfig.safe;
                  
                  return (
                    <motion.div
                      key={incident.id}
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ delay: idx * 0.03 }}
                      className={`rounded-lg border ${config.border} ${config.bg} overflow-hidden hover:border-white/20 transition-all cursor-pointer`}
                      onClick={() => viewIncidentDetails(incident.id)}
                      data-testid={`incident-card-${incident.id}`}
                    >
                      {/* Image Placeholder / Thumbnail */}
                      <div className="h-32 bg-black/50 flex items-center justify-center relative overflow-hidden">
                        {incident.frame_thumbnail ? (
                          <img 
                            src={`data:image/jpeg;base64,${incident.frame_thumbnail}`}
                            alt="Incident thumbnail"
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <Image className="w-12 h-12 text-muted-foreground/30" />
                        )}
                        <div className="absolute top-2 left-2">
                          <Badge className={`${config.bg} ${config.text} ${config.border} uppercase text-[10px]`}>
                            {incident.severity}
                          </Badge>
                        </div>
                        <div className="absolute top-2 right-2">
                          <span className="text-xs font-mono bg-black/60 px-2 py-1 rounded">
                            {Math.round(incident.confidence * 100)}%
                          </span>
                        </div>
                        {incident.movement_towards_exit && (
                          <div className="absolute bottom-2 right-2">
                            <Badge className="bg-red-500/80 text-white text-[9px]">
                              <ArrowRight className="w-3 h-3 mr-1" />
                              EXIT
                            </Badge>
                          </div>
                        )}
                        {incident.staff_theft && (
                          <div className="absolute bottom-2 left-2">
                            <Badge className="bg-purple-500/80 text-white text-[9px]">
                              <DollarSign className="w-3 h-3 mr-1" />
                              STAFF
                            </Badge>
                          </div>
                        )}
                      </div>
                      
                      {/* Content */}
                      <div className="p-3 space-y-2">
                        <p className="text-sm font-medium line-clamp-2">{incident.description}</p>
                        
                        {/* Items Involved */}
                        {incident.items_involved?.length > 0 && (
                          <div className="flex items-center gap-1 flex-wrap">
                            <Package className="w-3 h-3 text-muted-foreground" />
                            {incident.items_involved.slice(0, 3).map((item, i) => (
                              <Badge key={i} variant="outline" className="text-[9px] bg-white/5">
                                {item}
                              </Badge>
                            ))}
                            {incident.items_involved.length > 3 && (
                              <span className="text-[9px] text-muted-foreground">
                                +{incident.items_involved.length - 3} more
                              </span>
                            )}
                          </div>
                        )}
                        
                        {/* Concealment Method */}
                        {incident.concealment_method && incident.concealment_method !== "none" && (
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span>{concealmentIcons[incident.concealment_method]}</span>
                            <span className="capitalize">{incident.concealment_method} concealment</span>
                          </div>
                        )}
                        
                        {/* Behaviors */}
                        {incident.behaviors_detected?.length > 0 && (
                          <div className="flex flex-wrap gap-1">
                            {incident.behaviors_detected.slice(0, 2).map((behavior, i) => (
                              <Badge key={i} variant="outline" className="text-[9px] bg-white/5 border-white/10">
                                {behavior.length > 30 ? behavior.substring(0, 30) + "..." : behavior}
                              </Badge>
                            ))}
                          </div>
                        )}
                        
                        {/* Footer */}
                        <div className="flex items-center justify-between pt-2 border-t border-white/5 text-xs text-muted-foreground">
                          <span>{incident.video_name}</span>
                          <span>{formatDate(incident.timestamp)}</span>
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          ) : (
            <div className="p-12 text-center">
              <ShieldCheck className="w-16 h-16 text-emerald-500/30 mx-auto mb-4" />
              <p className="text-lg font-medium">No incidents found</p>
              <p className="text-sm text-muted-foreground mt-1">
                {searchQuery || severityFilter !== "all" || storeFilter !== "all"
                  ? "Try adjusting your filters"
                  : "Upload and analyze videos to detect incidents"}
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Incident Detail Dialog */}
      <Dialog open={!!selectedIncident} onOpenChange={() => { setSelectedIncident(null); setIncidentImage(null); }}>
        <DialogContent className="max-w-3xl bg-card border-white/10 max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Rajdhani, sans-serif' }} className="flex items-center gap-2">
              <AlertTriangle className={`w-5 h-5 ${severityConfig[selectedIncident?.severity]?.text}`} />
              INCIDENT DETAILS
            </DialogTitle>
            <DialogDescription>
              {selectedIncident?.video_name} • Frame {selectedIncident?.frame_index}
            </DialogDescription>
          </DialogHeader>
          
          {selectedIncident && (
            <div className="space-y-4">
              {/* Frame Image */}
              <div className="rounded-lg overflow-hidden bg-black/50 relative">
                {loadingImage ? (
                  <div className="h-64 flex items-center justify-center">
                    <div className="animate-spin w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full" />
                  </div>
                ) : incidentImage ? (
                  <img 
                    src={`data:image/jpeg;base64,${incidentImage}`}
                    alt="Incident frame"
                    className="w-full h-auto max-h-[400px] object-contain"
                  />
                ) : (
                  <div className="h-64 flex items-center justify-center">
                    <Image className="w-16 h-16 text-muted-foreground/30" />
                  </div>
                )}
                
                {/* Severity Badge */}
                <div className="absolute top-3 left-3">
                  <Badge className={`
                    ${severityConfig[selectedIncident.severity]?.bg} 
                    ${severityConfig[selectedIncident.severity]?.text} 
                    ${severityConfig[selectedIncident.severity]?.border}
                    uppercase
                  `}>
                    {selectedIncident.severity}
                  </Badge>
                </div>
                
                {/* Confidence */}
                <div className="absolute top-3 right-3">
                  <Badge className="bg-black/70 text-white">
                    {Math.round(selectedIncident.confidence * 100)}% confidence
                  </Badge>
                </div>
              </div>

              {/* Description */}
              <div className="p-4 rounded-lg bg-secondary/50">
                <p className="text-sm">{selectedIncident.description}</p>
              </div>

              {/* Detection Details Grid */}
              <div className="grid grid-cols-2 gap-4">
                {/* Person Description */}
                {selectedIncident.person_description && (
                  <div className="p-3 rounded-lg bg-secondary/30 border border-white/5">
                    <div className="flex items-center gap-2 mb-2">
                      <User className="w-4 h-4 text-blue-400" />
                      <span className="text-xs text-muted-foreground uppercase tracking-wider">Suspect Description</span>
                    </div>
                    <p className="text-sm">{selectedIncident.person_description}</p>
                  </div>
                )}
                
                {/* Items Involved */}
                {selectedIncident.items_involved?.length > 0 && (
                  <div className="p-3 rounded-lg bg-secondary/30 border border-white/5">
                    <div className="flex items-center gap-2 mb-2">
                      <Package className="w-4 h-4 text-amber-400" />
                      <span className="text-xs text-muted-foreground uppercase tracking-wider">Items Involved</span>
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {selectedIncident.items_involved.map((item, i) => (
                        <Badge key={i} variant="outline" className="bg-white/5">
                          {item}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Concealment & Movement */}
              <div className="flex gap-4">
                {selectedIncident.concealment_method && selectedIncident.concealment_method !== "none" && (
                  <div className="flex items-center gap-2 p-2 rounded bg-amber-500/10 border border-amber-500/30">
                    <span className="text-lg">{concealmentIcons[selectedIncident.concealment_method]}</span>
                    <span className="text-sm text-amber-400 capitalize">
                      {selectedIncident.concealment_method} Concealment
                    </span>
                  </div>
                )}
                
                {selectedIncident.movement_towards_exit && (
                  <div className="flex items-center gap-2 p-2 rounded bg-red-500/10 border border-red-500/30">
                    <ArrowRight className="w-4 h-4 text-red-400" />
                    <span className="text-sm text-red-400">Moving Towards Exit</span>
                  </div>
                )}
                
                {selectedIncident.staff_theft && (
                  <div className="flex items-center gap-2 p-2 rounded bg-purple-500/10 border border-purple-500/30">
                    <DollarSign className="w-4 h-4 text-purple-400" />
                    <span className="text-sm text-purple-400">Staff Theft Indicator</span>
                  </div>
                )}
              </div>

              {/* Behaviors Detected */}
              {selectedIncident.behaviors_detected?.length > 0 && (
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2">Detected Behaviors</p>
                  <div className="flex flex-wrap gap-2">
                    {selectedIncident.behaviors_detected.map((behavior, i) => (
                      <Badge key={i} variant="outline" className="bg-white/5 border-white/10">
                        {behavior}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Reasoning */}
              {selectedIncident.reasoning && (
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2">AI Analysis</p>
                  <p className="text-sm bg-secondary/30 p-3 rounded-lg">{selectedIncident.reasoning}</p>
                </div>
              )}

              {/* Metadata Grid */}
              <div className="grid grid-cols-4 gap-4 pt-4 border-t border-white/5">
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Frame</p>
                  <p className="font-mono">{selectedIncident.frame_index}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Time</p>
                  <p className="font-mono">{formatDate(selectedIncident.timestamp)}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Store Type</p>
                  <p className="capitalize">{selectedIncident.store_type}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Persons Detected</p>
                  <p>{selectedIncident.persons_detected || 0}</p>
                </div>
              </div>

              {/* Analysis Methods */}
              {selectedIncident.analysis_methods?.length > 0 && (
                <div className="flex items-center gap-2 pt-2">
                  <span className="text-xs text-muted-foreground">Analyzed by:</span>
                  {selectedIncident.analysis_methods.map((method, i) => (
                    <Badge key={i} variant="outline" className="text-[10px] bg-cyan-500/10 text-cyan-400 border-cyan-500/30">
                      {method}
                    </Badge>
                  ))}
                </div>
              )}
              
              {/* Actions */}
              <div className="flex gap-3 pt-4 border-t border-white/5">
                <button
                  onClick={() => { setSelectedIncident(null); setIncidentImage(null); }}
                  className="flex-1 py-2 rounded-sm bg-secondary border border-white/10 hover:bg-secondary/80"
                >
                  Close
                </button>
                <button
                  onClick={() => handleDelete(selectedIncident.id)}
                  className="px-4 py-2 rounded-sm bg-red-500/10 border border-red-500/30 text-red-500 hover:bg-red-500/20"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
