import { useState, useCallback } from "react";
import axios from "axios";
import { 
  Upload, 
  Video, 
  CheckCircle, 
  XCircle, 
  Loader2,
  AlertTriangle,
  Shield,
  FileVideo
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const storeTypes = [
  { value: "convenience", label: "Convenience Store" },
  { value: "liquor", label: "Liquor Store" },
  { value: "gas_station", label: "Gas Station" },
  { value: "retail", label: "Retail Store" },
];

export default function VideoUpload() {
  const [file, setFile] = useState(null);
  const [storeType, setStoreType] = useState("convenience");
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [uploadedVideo, setUploadedVideo] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile && droppedFile.type.startsWith("video/")) {
      setFile(droppedFile);
      setUploadedVideo(null);
      setAnalysisResult(null);
    } else {
      toast.error("Please upload a valid video file");
    }
  }, []);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setUploadedVideo(null);
      setAnalysisResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      toast.error("Please select a video file");
      return;
    }

    setUploading(true);
    setProgress(0);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("store_type", storeType);

      const response = await axios.post(`${API}/videos/upload`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (progressEvent) => {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setProgress(percent);
        },
      });

      setUploadedVideo(response.data);
      toast.success("Video uploaded successfully!");
    } catch (err) {
      console.error("Upload error:", err);
      toast.error(err.response?.data?.detail || "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!uploadedVideo?.id) {
      toast.error("Please upload a video first");
      return;
    }

    setAnalyzing(true);
    setProgress(0);

    try {
      // Start progress animation
      const progressInterval = setInterval(() => {
        setProgress((prev) => Math.min(prev + 5, 90));
      }, 2000);

      const response = await axios.post(`${API}/videos/${uploadedVideo.id}/analyze`);
      
      clearInterval(progressInterval);
      setProgress(100);
      setAnalysisResult(response.data);
      
      if (response.data.incidents_detected > 0) {
        toast.warning(`${response.data.incidents_detected} suspicious activities detected!`, {
          icon: <AlertTriangle className="w-5 h-5 text-amber-500" />,
        });
      } else {
        toast.success("Analysis complete. No suspicious activity detected.", {
          icon: <Shield className="w-5 h-5 text-emerald-500" />,
        });
      }
    } catch (err) {
      console.error("Analysis error:", err);
      toast.error(err.response?.data?.detail || "Analysis failed");
    } finally {
      setAnalyzing(false);
    }
  };

  const resetUpload = () => {
    setFile(null);
    setUploadedVideo(null);
    setAnalysisResult(null);
    setProgress(0);
  };

  return (
    <div className="p-6 space-y-6" data-testid="video-upload-page">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
          VIDEO ANALYSIS
        </h1>
        <p className="text-muted-foreground mt-1">
          Upload security footage for AI-powered shoplifting detection
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload Section */}
        <Card className="bg-card/50 border-white/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
              <Upload className="w-5 h-5 text-blue-500" />
              UPLOAD VIDEO
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Store Type Selection */}
            <div>
              <label className="text-sm text-muted-foreground mb-2 block">Store Type</label>
              <Select value={storeType} onValueChange={setStoreType}>
                <SelectTrigger className="bg-secondary border-white/10" data-testid="store-type-select">
                  <SelectValue placeholder="Select store type" />
                </SelectTrigger>
                <SelectContent>
                  {storeTypes.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      {type.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Dropzone */}
            <div
              className={`dropzone ${dragActive ? "active" : ""}`}
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              onClick={() => document.getElementById("file-input").click()}
              data-testid="dropzone"
            >
              <input
                id="file-input"
                type="file"
                accept="video/*"
                onChange={handleFileChange}
                className="hidden"
                data-testid="file-input"
              />
              
              {file ? (
                <div className="flex flex-col items-center gap-3">
                  <FileVideo className="w-12 h-12 text-blue-500" />
                  <div className="text-center">
                    <p className="font-medium">{file.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {(file.size / (1024 * 1024)).toFixed(2)} MB
                    </p>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3">
                  <Video className="w-12 h-12 text-muted-foreground" />
                  <div className="text-center">
                    <p className="font-medium">Drop your video here</p>
                    <p className="text-sm text-muted-foreground">
                      or click to browse (MP4, MOV, AVI)
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Progress Bar */}
            {(uploading || analyzing) && (
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">
                    {uploading ? "Uploading..." : "Analyzing frames..."}
                  </span>
                  <span className="font-mono text-cyan-400">{progress}%</span>
                </div>
                <Progress value={progress} className="h-2" />
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-3">
              {!uploadedVideo ? (
                <button
                  onClick={handleUpload}
                  disabled={!file || uploading}
                  className="btn-primary flex-1 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  data-testid="upload-btn"
                >
                  {uploading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4" />
                      Upload Video
                    </>
                  )}
                </button>
              ) : !analysisResult ? (
                <button
                  onClick={handleAnalyze}
                  disabled={analyzing}
                  className="btn-primary flex-1 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                  data-testid="analyze-btn"
                >
                  {analyzing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      <Shield className="w-4 h-4" />
                      Start Analysis
                    </>
                  )}
                </button>
              ) : (
                <button
                  onClick={resetUpload}
                  className="btn-primary flex-1 flex items-center justify-center gap-2"
                  data-testid="reset-btn"
                >
                  <Upload className="w-4 h-4" />
                  Upload Another
                </button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Results Section */}
        <Card className="bg-card/50 border-white/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
              <Shield className="w-5 h-5 text-cyan-400" />
              ANALYSIS RESULTS
            </CardTitle>
          </CardHeader>
          <CardContent>
            <AnimatePresence mode="wait">
              {analysisResult ? (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="space-y-6"
                  data-testid="analysis-results"
                >
                  {/* Summary Stats */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 rounded-md bg-secondary/50 border border-white/5">
                      <p className="text-2xl font-bold" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                        {analysisResult.frames_analyzed}
                      </p>
                      <p className="text-xs text-muted-foreground uppercase tracking-wider">
                        Frames Analyzed
                      </p>
                    </div>
                    <div className={`p-4 rounded-md border ${
                      analysisResult.incidents_detected > 0 
                        ? "bg-red-500/10 border-red-500/30" 
                        : "bg-emerald-500/10 border-emerald-500/30"
                    }`}>
                      <p className={`text-2xl font-bold ${
                        analysisResult.incidents_detected > 0 ? "text-red-500" : "text-emerald-500"
                      }`} style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                        {analysisResult.incidents_detected}
                      </p>
                      <p className="text-xs text-muted-foreground uppercase tracking-wider">
                        Incidents Detected
                      </p>
                    </div>
                  </div>

                  {/* Incidents List */}
                  {analysisResult.incidents?.length > 0 ? (
                    <div className="space-y-3">
                      <h4 className="text-sm font-medium uppercase tracking-wider text-muted-foreground">
                        Detected Incidents
                      </h4>
                      {analysisResult.incidents.map((incident, idx) => (
                        <div
                          key={incident.id || idx}
                          className={`p-4 rounded-md border ${
                            incident.severity === "critical"
                              ? "bg-red-500/10 border-red-500/30"
                              : incident.severity === "warning"
                              ? "bg-amber-500/10 border-amber-500/30"
                              : "bg-emerald-500/10 border-emerald-500/30"
                          }`}
                          data-testid={`incident-result-${idx}`}
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex-1">
                              <p className="text-sm font-medium">{incident.description}</p>
                              {incident.behaviors?.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-2">
                                  {incident.behaviors.map((behavior, i) => (
                                    <Badge 
                                      key={i} 
                                      variant="outline" 
                                      className="text-[10px] bg-white/5"
                                    >
                                      {behavior}
                                    </Badge>
                                  ))}
                                </div>
                              )}
                            </div>
                            <div className="text-right">
                              <Badge
                                className={`uppercase text-[10px] ${
                                  incident.severity === "critical"
                                    ? "bg-red-500/20 text-red-500 border-red-500/30"
                                    : incident.severity === "warning"
                                    ? "bg-amber-500/20 text-amber-500 border-amber-500/30"
                                    : "bg-emerald-500/20 text-emerald-500 border-emerald-500/30"
                                }`}
                              >
                                {incident.severity}
                              </Badge>
                              <p className="text-xs text-muted-foreground font-mono mt-1">
                                {Math.round(incident.confidence * 100)}% conf
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-center py-8">
                      <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
                      <p className="font-medium text-emerald-500">All Clear</p>
                      <p className="text-sm text-muted-foreground mt-1">
                        No suspicious activity detected in this footage
                      </p>
                    </div>
                  )}
                </motion.div>
              ) : uploadedVideo ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="text-center py-8"
                  data-testid="ready-to-analyze"
                >
                  <Video className="w-12 h-12 text-blue-500 mx-auto mb-3" />
                  <p className="font-medium">Video Ready</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    {uploadedVideo.filename} ({Math.round(uploadedVideo.duration_seconds)}s)
                  </p>
                  <p className="text-xs text-cyan-400 mt-3">
                    Click "Start Analysis" to begin AI detection
                  </p>
                </motion.div>
              ) : (
                <div className="text-center py-8" data-testid="no-video">
                  <Shield className="w-12 h-12 text-muted-foreground/30 mx-auto mb-3" />
                  <p className="text-muted-foreground">No video uploaded</p>
                  <p className="text-sm text-muted-foreground/60 mt-1">
                    Upload a video to see analysis results
                  </p>
                </div>
              )}
            </AnimatePresence>
          </CardContent>
        </Card>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-md bg-blue-500/10 border border-blue-500/30">
              <Video className="w-6 h-6 text-blue-500" />
            </div>
            <div>
              <p className="font-medium" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                Supported Formats
              </p>
              <p className="text-sm text-muted-foreground">MP4, MOV, AVI, WEBM</p>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-md bg-cyan-500/10 border border-cyan-500/30">
              <Shield className="w-6 h-6 text-cyan-400" />
            </div>
            <div>
              <p className="font-medium" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                AI-Powered
              </p>
              <p className="text-sm text-muted-foreground">GPT-5.2 Vision Analysis</p>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-card/50 border-white/5">
          <CardContent className="p-4 flex items-center gap-4">
            <div className="p-3 rounded-md bg-emerald-500/10 border border-emerald-500/30">
              <CheckCircle className="w-6 h-6 text-emerald-500" />
            </div>
            <div>
              <p className="font-medium" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                Detection Types
              </p>
              <p className="text-sm text-muted-foreground">Concealment, Loitering, etc.</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
