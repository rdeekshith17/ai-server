import { useState, useEffect, useRef, useCallback } from "react";
import axios from "axios";
import { 
  Camera, 
  Play, 
  Pause, 
  AlertTriangle, 
  User,
  Activity,
  Shield,
  Video,
  RefreshCw,
  Settings,
  Maximize2
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Slider } from "../components/ui/slider";
import { toast } from "sonner";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const threatColors = {
  safe: { bg: "bg-emerald-500/20", border: "border-emerald-500/50", text: "text-emerald-400" },
  warning: { bg: "bg-amber-500/20", border: "border-amber-500/50", text: "text-amber-400" },
  critical: { bg: "bg-red-500/20", border: "border-red-500/50", text: "text-red-400" }
};

const sceneStatusColors = {
  normal: { bg: "bg-emerald-500", text: "NORMAL" },
  alert: { bg: "bg-amber-500", text: "ALERT" },
  critical: { bg: "bg-red-500 animate-pulse", text: "CRITICAL" }
};

export default function LiveFeed() {
  const [videos, setVideos] = useState([]);
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [totalFrames, setTotalFrames] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [frameData, setFrameData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [autoProcess, setAutoProcess] = useState(true);
  const [error, setError] = useState(null);
  const playIntervalRef = useRef(null);

  useEffect(() => {
    fetchVideos();
    return () => {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
      }
    };
  }, []);

  useEffect(() => {
    if (selectedVideo && autoProcess) {
      processCurrentFrame();
    }
  }, [selectedVideo, currentFrame]);

  useEffect(() => {
    if (isPlaying && selectedVideo) {
      playIntervalRef.current = setInterval(() => {
        setCurrentFrame(prev => {
          if (prev >= totalFrames - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 3; // Skip 3 frames for faster playback
        });
      }, 500); // Process every 500ms
    } else {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
      }
    }
    
    return () => {
      if (playIntervalRef.current) {
        clearInterval(playIntervalRef.current);
      }
    };
  }, [isPlaying, selectedVideo, totalFrames]);

  const fetchVideos = async () => {
    try {
      const response = await axios.get(`${API}/videos`);
      const completedVideos = (response.data.videos || []).filter(v => v.status === "completed" || v.temp_path);
      setVideos(completedVideos);
    } catch (err) {
      console.error("Failed to fetch videos:", err);
    }
  };

  const processCurrentFrame = async () => {
    if (!selectedVideo) return;
    
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(
        `${API}/live/process-video-frame?video_id=${selectedVideo.id}&frame_number=${currentFrame}`
      );
      setFrameData(response.data);
      setTotalFrames(response.data.total_frames || 0);
    } catch (err) {
      console.error("Frame processing error:", err);
      const detail = err.response?.data?.detail || "Processing failed";
      setError(detail);
      if (detail.includes("Video file not found")) {
        toast.error("Video file not available. Please upload the video again in Upload section.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleVideoSelect = (videoId) => {
    const video = videos.find(v => v.id === videoId);
    setSelectedVideo(video);
    setCurrentFrame(0);
    setFrameData(null);
    setIsPlaying(false);
  };

  const togglePlayback = () => {
    setIsPlaying(!isPlaying);
  };

  const handleSliderChange = (value) => {
    setCurrentFrame(value[0]);
    setIsPlaying(false);
  };

  const getDetectionCount = () => {
    return frameData?.detections?.length || 0;
  };

  const getSuspiciousCount = () => {
    return frameData?.detections?.filter(d => d.threat_level !== "safe").length || 0;
  };

  return (
    <div className="p-6 space-y-6" data-testid="live-feed-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
            LIVE DETECTION
          </h1>
          <p className="text-muted-foreground mt-1">
            Real-time AI detection with pose estimation and activity tracking
          </p>
        </div>
        
        {/* Scene Status Badge */}
        {frameData?.scene_analysis && (
          <div className={`px-4 py-2 rounded-sm ${sceneStatusColors[frameData.scene_analysis.scene_status]?.bg} text-white font-bold uppercase tracking-wider`}>
            {sceneStatusColors[frameData.scene_analysis.scene_status]?.text}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Video Feed */}
        <div className="lg:col-span-2 space-y-4">
          <Card className="bg-card/50 border-white/5 overflow-hidden">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                  <Camera className="w-5 h-5 text-cyan-400" />
                  VIDEO FEED
                </CardTitle>
                
                {/* Video Selector */}
                <Select value={selectedVideo?.id || ""} onValueChange={handleVideoSelect}>
                  <SelectTrigger className="w-[250px] bg-secondary border-white/10">
                    <SelectValue placeholder="Select a video..." />
                  </SelectTrigger>
                  <SelectContent>
                    {videos.map(video => (
                      <SelectItem key={video.id} value={video.id}>
                        {video.filename}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            
            <CardContent className="p-0">
              {/* Video Frame Display */}
              <div className="relative aspect-video bg-black flex items-center justify-center">
                {loading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10">
                    <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
                  </div>
                )}
                
                {frameData?.frame_annotated ? (
                  <img 
                    src={`data:image/jpeg;base64,${frameData.frame_annotated}`}
                    alt="Detection feed"
                    className="w-full h-full object-contain"
                  />
                ) : (
                  <div className="text-center text-muted-foreground">
                    <Video className="w-16 h-16 mx-auto mb-4 opacity-30" />
                    <p>Select a video to start live detection</p>
                    <p className="text-sm mt-2">Or upload a new video in the Upload section</p>
                  </div>
                )}
                
                {/* Overlay Info */}
                {frameData && (
                  <>
                    {/* Frame Counter */}
                    <div className="absolute top-3 left-3 px-2 py-1 bg-black/70 rounded text-xs font-mono text-white">
                      Frame: {currentFrame} / {totalFrames}
                    </div>
                    
                    {/* Detection Counter */}
                    <div className="absolute top-3 right-3 flex gap-2">
                      <div className="px-2 py-1 bg-blue-500/70 rounded text-xs font-mono text-white flex items-center gap-1">
                        <User className="w-3 h-3" />
                        {getDetectionCount()} detected
                      </div>
                      {getSuspiciousCount() > 0 && (
                        <div className="px-2 py-1 bg-red-500/70 rounded text-xs font-mono text-white flex items-center gap-1 animate-pulse">
                          <AlertTriangle className="w-3 h-3" />
                          {getSuspiciousCount()} suspicious
                        </div>
                      )}
                    </div>
                    
                    {/* Timestamp */}
                    <div className="absolute bottom-3 left-3 px-2 py-1 bg-black/70 rounded text-xs font-mono text-cyan-400">
                      {new Date(frameData.timestamp).toLocaleTimeString()}
                    </div>
                  </>
                )}
              </div>
              
              {/* Playback Controls */}
              {selectedVideo && (
                <div className="p-4 border-t border-white/5 space-y-4">
                  {/* Timeline Slider */}
                  <div className="space-y-2">
                    <Slider
                      value={[currentFrame]}
                      onValueChange={handleSliderChange}
                      max={Math.max(totalFrames - 1, 1)}
                      step={1}
                      className="cursor-pointer"
                    />
                  </div>
                  
                  {/* Control Buttons */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={togglePlayback}
                        className="bg-secondary border-white/10"
                      >
                        {isPlaying ? (
                          <><Pause className="w-4 h-4 mr-2" /> Pause</>
                        ) : (
                          <><Play className="w-4 h-4 mr-2" /> Play</>
                        )}
                      </Button>
                      
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={processCurrentFrame}
                        disabled={loading}
                        className="bg-secondary border-white/10"
                      >
                        <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                        Process Frame
                      </Button>
                    </div>
                    
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>Frame: {currentFrame}</span>
                      <span>|</span>
                      <span>Total: {totalFrames}</span>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Detection Panel */}
        <div className="space-y-4">
          {/* Scene Analysis */}
          <Card className="bg-card/50 border-white/5">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                <Activity className="w-4 h-4 text-purple-400" />
                SCENE ANALYSIS
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {frameData?.scene_analysis ? (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Persons Detected</span>
                    <span className="font-mono text-lg">{frameData.scene_analysis.total_persons}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Suspicious Activity</span>
                    <span className={`font-mono text-lg ${frameData.scene_analysis.suspicious_count > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                      {frameData.scene_analysis.suspicious_count}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Scene Status</span>
                    <Badge className={`${sceneStatusColors[frameData.scene_analysis.scene_status]?.bg} uppercase`}>
                      {frameData.scene_analysis.scene_status}
                    </Badge>
                  </div>
                  
                  {/* Activities Summary */}
                  {Object.keys(frameData.scene_analysis.activities_summary || {}).length > 0 && (
                    <div className="pt-3 border-t border-white/5">
                      <p className="text-xs text-muted-foreground uppercase tracking-wider mb-2">Activities</p>
                      <div className="flex flex-wrap gap-1">
                        {Object.entries(frameData.scene_analysis.activities_summary).map(([activity, count]) => (
                          <Badge 
                            key={activity} 
                            variant="outline" 
                            className={`text-[10px] ${
                              activity.includes('pocket') || activity.includes('concealment') 
                                ? 'bg-red-500/10 text-red-400 border-red-500/30' 
                                : 'bg-white/5'
                            }`}
                          >
                            {activity.replace(/_/g, ' ')}: {count}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="text-center py-4 text-muted-foreground text-sm">
                  No analysis data
                </div>
              )}
            </CardContent>
          </Card>

          {/* Individual Detections */}
          <Card className="bg-card/50 border-white/5">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                <User className="w-4 h-4 text-blue-400" />
                PERSON DETECTIONS
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 max-h-[400px] overflow-y-auto">
              {frameData?.detections?.length > 0 ? (
                frameData.detections.map((det, idx) => {
                  const colors = threatColors[det.threat_level] || threatColors.safe;
                  return (
                    <div 
                      key={idx}
                      className={`p-3 rounded-lg ${colors.bg} border ${colors.border}`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium">Person {idx + 1}</span>
                        <Badge className={`${colors.bg} ${colors.text} border ${colors.border} uppercase text-[10px]`}>
                          {det.threat_level}
                        </Badge>
                      </div>
                      
                      {/* Position */}
                      <div className="text-xs text-muted-foreground mb-2">
                        Position: {det.position?.replace(/_/g, ' ') || 'Unknown'}
                      </div>
                      
                      {/* Activities */}
                      {det.activities?.length > 0 && (
                        <div className="space-y-1">
                          {det.activities.map((activity, i) => {
                            const score = det.activity_scores?.[activity] || 0;
                            const isHighRisk = activity.includes('pocket') || activity.includes('concealment');
                            return (
                              <div key={i} className="flex items-center justify-between">
                                <span className={`text-xs ${isHighRisk ? 'text-red-400' : 'text-muted-foreground'}`}>
                                  {activity.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                                </span>
                                <span className={`text-xs font-mono ${isHighRisk ? 'text-red-400' : ''}`}>
                                  {(score * 100).toFixed(1)}%
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      )}
                      
                      {/* Threat Score */}
                      {det.threat_score > 0 && (
                        <div className="mt-2 pt-2 border-t border-white/10 flex items-center justify-between">
                          <span className="text-xs text-muted-foreground">Threat Score</span>
                          <span className={`text-sm font-mono ${det.threat_score > 0.5 ? 'text-red-400' : 'text-amber-400'}`}>
                            {(det.threat_score * 100).toFixed(0)}%
                          </span>
                        </div>
                      )}
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-8 text-muted-foreground text-sm">
                  <User className="w-8 h-8 mx-auto mb-2 opacity-30" />
                  No persons detected
                </div>
              )}
            </CardContent>
          </Card>

          {/* ML Models Status */}
          <Card className="bg-card/50 border-white/5">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm" style={{ fontFamily: 'Rajdhani, sans-serif' }}>
                <Shield className="w-4 h-4 text-cyan-400" />
                ACTIVE MODELS
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-purple-400 animate-pulse" />
                <span className="text-xs text-muted-foreground">YOLO v8 - Person Detection</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-pink-400 animate-pulse" />
                <span className="text-xs text-muted-foreground">YOLO Pose - Skeleton Tracking</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                <span className="text-xs text-muted-foreground">Decision Engine - Threat Assessment</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
