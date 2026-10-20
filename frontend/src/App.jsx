import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import CodeStudio from './pages/CodeStudio';
import Architecture from './pages/Architecture';
import RagVectors from './pages/RagVectors';
import PaperViva from './pages/PaperViva';
import GatewayModal from './components/GatewayModal';
import BenchmarkModal from './components/BenchmarkModal';
import DocumentationModal from './components/DocumentationModal';
import { fetchStatus } from './services/api';
import { Shield, Sparkles, CheckCircle2 } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('studio');
  const [gatewayStatus, setGatewayStatus] = useState(null);
  const [isGatewayModalOpen, setIsGatewayModalOpen] = useState(false);
  const [isBenchmarkModalOpen, setIsBenchmarkModalOpen] = useState(false);
  const [isDocsModalOpen, setIsDocsModalOpen] = useState(false);
  const [requestedSampleLang, setRequestedSampleLang] = useState(null);

  const loadStatus = () => {
    fetchStatus()
      .then(data => {
        setGatewayStatus(data.gateway);
      })
      .catch(err => {
        console.error("Could not fetch gateway status:", err);
      });
  };

  useEffect(() => {
    loadStatus();
    // Periodic status refresh every 15s (paused when tab is hidden)
    const interval = setInterval(() => {
      if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
        loadStatus();
      }
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const getPageTitle = () => {
    switch (activeTab) {
      case 'studio': return { title: 'Code Studio', badge: 'Primary Workspace' };
      case 'architecture': return { title: 'Architecture & LangGraph', badge: 'Deterministic Pipeline' };
      case 'rag': return { title: 'RAG Explorer', badge: 'OWASP / CWE Vectors' };
      case 'reports': return { title: 'Reports & Viva Defense', badge: 'Certified Telemetry' };
      default: return { title: 'PR Agent', badge: 'AG-12 Protocol' };
    }
  };

  const { title: pageTitle, badge: pageBadge } = getPageTitle();

  return (
    <div className="min-h-screen bg-[#F3F5F8] text-[#343A40] antialiased flex flex-col">
      
      {/* Keyboard Accessibility Skip Link */}
      <a href="#main-content" className="skip-to-content focus:outline-none">
        Skip to main content
      </a>

      {/* Navy Sidebar & Responsive Mobile Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        gatewayStatus={gatewayStatus}
        onOpenBenchmark={() => setIsBenchmarkModalOpen(true)}
        onOpenSettings={() => setIsGatewayModalOpen(true)}
        onOpenDocs={() => setIsDocsModalOpen(true)}
      />

      {/* Main Content Area Offset on Desktop for Fixed Navy Sidebar */}
      <div className="flex-1 flex flex-col lg:pl-64 xl:pl-72 min-w-0">
        
        {/* Workspace Top Breadcrumb Header */}
        <header className="bg-white border-b border-[#E2E6EC] px-4 sm:px-6 lg:px-8 py-4 shadow-xs sticky top-0 z-20 hidden sm:block">
          <div className="max-w-[1600px] mx-auto flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <h2 className="text-lg font-bold text-[#142B4A] tracking-tight">
                {pageTitle}
              </h2>
              <span className="px-2.5 py-0.5 text-xs font-mono font-semibold rounded-md bg-[#DCE7F5] text-[#142B4A] border border-[#B8D0EC]">
                {pageBadge}
              </span>
            </div>

            <div className="flex items-center space-x-3 text-xs text-[#606973] font-mono">
              <span className="flex items-center space-x-1.5">
                <span className="w-2 h-2 rounded-full bg-[#10B981]" />
                <span className="font-semibold text-[#142B4A]">Multi-Agent Protocol Active</span>
              </span>
              <span>·</span>
              <span>Dual-Attribution Grounding</span>
            </div>
          </div>
        </header>

        {/* Dynamic Workspace Container */}
        <main 
          id="main-content" 
          tabIndex="-1" 
          className="flex-1 w-full max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 focus:outline-none"
        >
          {activeTab === 'studio' && (
            <CodeStudio
              gatewayStatus={gatewayStatus}
              onOpenSettings={() => setIsGatewayModalOpen(true)}
              requestedSampleLang={requestedSampleLang}
              onOpenBenchmark={() => setIsBenchmarkModalOpen(true)}
            />
          )}
          {activeTab === 'architecture' && <Architecture />}
          {activeTab === 'rag' && <RagVectors />}
          {activeTab === 'reports' && <PaperViva />}
        </main>

        {/* Clean Light-Grey Footer with Neutral Grey Border */}
        <footer className="border-t border-[#E2E6EC] bg-white py-6 mt-12 text-[#606973] text-xs font-sans">
          <div className="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-3">
            <div className="flex items-center space-x-2.5">
              <span className="font-bold text-[#142B4A]">AG-12 Protocol</span>
              <span className="text-[#CBD5E1]">·</span>
              <span>Autonomous Code Review &amp; Auto-Correction Engine</span>
            </div>
            <div className="flex items-center space-x-3 text-xs font-mono text-[#606973]">
              <span>LangGraph Engine</span>
              <span>·</span>
              <span>MCP Static Analysis</span>
              <span>·</span>
              <span>Grounded RAG</span>
              <span>·</span>
              <span className="text-[#142B4A] font-bold">PR Agent</span>
            </div>
          </div>
        </footer>

      </div>

      {/* Modals */}
      <GatewayModal
        isOpen={isGatewayModalOpen}
        onClose={() => setIsGatewayModalOpen(false)}
        gatewayStatus={gatewayStatus}
        onUpdate={(updated) => setGatewayStatus(updated)}
      />

      <BenchmarkModal
        isOpen={isBenchmarkModalOpen}
        onClose={() => setIsBenchmarkModalOpen(false)}
        onLoadSampleCode={(lang) => {
          setRequestedSampleLang(lang);
          setActiveTab('studio');
        }}
      />

      <DocumentationModal
        isOpen={isDocsModalOpen}
        onClose={() => setIsDocsModalOpen(false)}
      />

    </div>
  );
}
