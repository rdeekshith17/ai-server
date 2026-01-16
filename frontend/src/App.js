import { BrowserRouter, Routes, Route } from "react-router-dom";
import "@/App.css";
import Layout from "./components/Layout";
import Dashboard from "./pages/Dashboard";
import VideoUpload from "./pages/VideoUpload";
import Incidents from "./pages/Incidents";
import Analytics from "./pages/Analytics";
import Watchlist from "./pages/Watchlist";
import LiveFeed from "./pages/LiveFeed";
import { Toaster } from "./components/ui/sonner";

function App() {
  return (
    <div className="App noise-overlay">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="upload" element={<VideoUpload />} />
            <Route path="live" element={<LiveFeed />} />
            <Route path="watchlist" element={<Watchlist />} />
            <Route path="incidents" element={<Incidents />} />
            <Route path="analytics" element={<Analytics />} />
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" theme="dark" />
    </div>
  );
}

export default App;
