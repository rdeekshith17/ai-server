import { useState, useEffect } from "react";
import axios from "axios";
import { 
  AlertTriangle, 
  Filter, 
  Trash2, 
  ShieldCheck,
  Search,
  Eye,
  ChevronDown
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

export default function Incidents() {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [storeFilter, setStoreFilter] = useState("all");
  const [selectedIncident, setSelectedIncident] = useState(null);

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

  const filteredIncidents = incidents.filter(incident => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      incident.description?.toLowerCase().includes(query) ||
      incident.video_name?.toLowerCase().includes(query) ||
      incident.behaviors_detected?.some(b => b.toLowerCase().includes(query))
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
            View and manage detected security incidents
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
                placeholder="Search incidents..."
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

      {/* Incidents List */}
      <Card className="bg-card/50 border-white/5">
        <CardHeader className="pb-0">
          <CardTitle className="flex items-center gap-2" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            <AlertTriangle className="w-5 h-5 text-amber-500" />
            INCIDENTS ({filteredIncidents.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0 mt-4">
          {loading ? (
            <div className="p-8 space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="skeleton h-20 rounded-md" />
              ))}
            </div>
          ) : filteredIncidents.length > 0 ? (
            <ScrollArea className="h-[500px]">
              <div className="divide-y divide-white/5">
                <AnimatePresence>
                  {filteredIncidents.map((incident, idx) => {
                    const config = severityConfig[incident.severity] || severityConfig.safe;
                    
                    return (
                      <motion.div
                        key={incident.id}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        exit={{ opacity: 0, x: 20 }}
                        transition={{ delay: idx * 0.05 }}
                        className="p-4 hover:bg-white/[0.02] transition-colors"
                        data-testid={`incident-row-${incident.id}`}
                      >
                        <div className="flex items-start gap-4">
                          {/* Severity Icon */}
                          <div className={`p-2 rounded-md ${config.bg} border ${config.border}`}>
                            <AlertTriangle className={`w-5 h-5 ${config.icon}`} />
                          </div>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <p className="font-medium">{incident.description}</p>
                                <p className="text-sm text-muted-foreground mt-0.5">
                                  {incident.video_name} • {formatDate(incident.timestamp)}
                                </p>
                              </div>
                              <div className="flex items-center gap-2">
                                <Badge className={`${config.bg} ${config.text} ${config.border} uppercase text-[10px]`}>
                                  {incident.severity}
                                </Badge>
                                <span className="text-sm font-mono text-muted-foreground">
                                  {Math.round(incident.confidence * 100)}%
                                </span>
                              </div>
                            </div>

                            {/* Behaviors */}
                            {incident.behaviors_detected?.length > 0 && (
                              <div className="flex flex-wrap gap-1 mt-2">
                                {incident.behaviors_detected.map((behavior, i) => (
                                  <Badge 
                                    key={i} 
                                    variant="outline" 
                                    className="text-[10px] bg-white/5 border-white/10"
                                  >
                                    {behavior}
                                  </Badge>
                                ))}
                              </div>
                            )}
                          </div>

                          {/* Actions */}
                          <DropdownMenu>
                            <DropdownMenuTrigger className="p-2 hover:bg-white/5 rounded-md">
                              <ChevronDown className="w-4 h-4 text-muted-foreground" />
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => setSelectedIncident(incident)}>
                                <Eye className="w-4 h-4 mr-2" />
                                View Details
                              </DropdownMenuItem>
                              <DropdownMenuItem 
                                onClick={() => handleDelete(incident.id)}
                                className="text-red-500 focus:text-red-500"
                              >
                                <Trash2 className="w-4 h-4 mr-2" />
                                Delete
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </motion.div>
                    );
                  })}
                </AnimatePresence>
              </div>
            </ScrollArea>
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
      <Dialog open={!!selectedIncident} onOpenChange={() => setSelectedIncident(null)}>
        <DialogContent className="max-w-lg bg-card border-white/10">
          <DialogHeader>
            <DialogTitle style={{ fontFamily: 'Rajdhani, sans-serif' }}>
              INCIDENT DETAILS
            </DialogTitle>
            <DialogDescription>
              {selectedIncident?.video_name}
            </DialogDescription>
          </DialogHeader>
          
          {selectedIncident && (
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <Badge className={`
                  ${severityConfig[selectedIncident.severity]?.bg} 
                  ${severityConfig[selectedIncident.severity]?.text} 
                  ${severityConfig[selectedIncident.severity]?.border}
                  uppercase
                `}>
                  {selectedIncident.severity}
                </Badge>
                <span className="text-sm text-muted-foreground font-mono">
                  {Math.round(selectedIncident.confidence * 100)}% confidence
                </span>
              </div>

              <div>
                <p className="text-sm text-muted-foreground mb-1">Description</p>
                <p>{selectedIncident.description}</p>
              </div>

              {selectedIncident.reasoning && (
                <div>
                  <p className="text-sm text-muted-foreground mb-1">AI Analysis</p>
                  <p className="text-sm">{selectedIncident.reasoning}</p>
                </div>
              )}

              {selectedIncident.behaviors_detected?.length > 0 && (
                <div>
                  <p className="text-sm text-muted-foreground mb-2">Detected Behaviors</p>
                  <div className="flex flex-wrap gap-2">
                    {selectedIncident.behaviors_detected.map((behavior, i) => (
                      <Badge key={i} variant="outline" className="bg-white/5">
                        {behavior}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-white/5">
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
                  <p className="text-xs text-muted-foreground uppercase tracking-wider">Location</p>
                  <p>{selectedIncident.location}</p>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
