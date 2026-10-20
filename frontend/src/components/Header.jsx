import React, { useState, memo } from 'react';
import { 
  Shield, Cpu, Activity, Database, FileText, Zap, Settings, 
  BookOpen, Menu, X, ChevronRight, CheckCircle2, Sparkles, Code2 
} from 'lucide-react';

function Header({
  activeTab,
  setActiveTab,
  gatewayStatus,
  onOpenBenchmark,
  onOpenSettings,
  onOpenDocs
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const provider = (gatewayStatus?.provider || "OLLAMA").toUpperCase();
  const model = (gatewayStatus?.model || "qwen2.5-coder:7b").toLowerCase();
  const fallbackState = gatewayStatus?.fallback_state || "standby";
  const isFallbackActive = gatewayStatus?.fallback_active || false;
  const status = gatewayStatus?.status || "Connected";
  const isConnected = status === "Connected" || status === "online";

  const navItems = [
    { id: 'studio', label: 'Code Studio', icon: Code2, desc: 'Editor & Multi-Agent Review' },
    { id: 'architecture', label: 'Architecture', icon: Activity, desc: 'LangGraph & MCP Pipeline' },
    { id: 'rag', label: 'RAG Explorer', icon: Database, desc: 'Vector Store & Standards' },
    { id: 'reports', label: 'Reports & History', icon: FileText, desc: 'Certified Audits & Viva' },
  ];

  const handleNavClick = (id) => {
    setActiveTab(id);
    setMobileMenuOpen(false);
  };

  return (
    <>
      {/* =========================================================================
          MOBILE TOP NAVBAR (Visible on < lg screens)
          ========================================================================= */}
      <header className="lg:hidden sticky top-0 z-40 bg-[#142B4A] text-white border-b border-[#1C3B65] px-4 py-3 shadow-sm">
        <div className="flex items-center justify-between">
          
          {/* Mobile Menu Toggle & Brand */}
          <div className="flex items-center space-x-3">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-lg bg-[#1C3B65] text-[#DCE7F5] hover:text-white transition-colors cursor-pointer"
              aria-label={mobileMenuOpen ? "Close menu" : "Open navigation menu"}
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>

            <button
              onClick={() => handleNavClick('studio')}
              className="flex items-center space-x-2.5 text-left cursor-pointer"
              aria-label="AG-12 Protocol Home"
            >
              <div className="w-8 h-8 rounded-lg bg-[#1C3B65] text-white flex items-center justify-center shadow-xs">
                <Shield className="w-4 h-4 text-white" />
              </div>
              <div className="flex items-center space-x-1.5">
                <span className="font-bold text-base tracking-tight text-white">AG-12</span>
                <span className="px-1.5 py-0.5 text-[10px] font-mono font-bold uppercase rounded bg-[#E9E2F5] text-[#4A2E7A]">
                  PR Agent
                </span>
              </div>
            </button>
          </div>

          {/* Right: Gateway Mini Pill */}
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={onOpenSettings}
              className="flex items-center space-x-2 bg-[#1C3B65] hover:bg-[#264B7D] text-[#DCE7F5] px-2.5 py-1.5 rounded-lg text-xs font-mono transition-colors cursor-pointer"
              title="Configure LLM Gateway"
            >
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-[#10B981]' : 'bg-[#F59E0B]'}`} />
              <span className="font-semibold">{provider}</span>
              <Settings className="w-3.5 h-3.5 text-[#DCE7F5]" />
            </button>
          </div>

        </div>
      </header>

      {/* =========================================================================
          MOBILE SLIDE-OVER DRAWER (Visible when mobile menu is open)
          ========================================================================= */}
      {mobileMenuOpen && (
        <div 
          className="lg:hidden fixed inset-0 z-50 bg-[#0E1F36]/60 backdrop-blur-xs flex"
          onClick={() => setMobileMenuOpen(false)}
        >
          <div 
            className="w-72 bg-[#142B4A] text-white h-full flex flex-col p-5 shadow-2xl animate-in slide-in-from-left duration-200"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Mobile Navigation Drawer"
          >
            <div className="flex items-center justify-between pb-4 border-b border-[#1C3B65]">
              <div className="flex items-center space-x-2.5">
                <div className="w-9 h-9 rounded-xl bg-[#1C3B65] flex items-center justify-center">
                  <Shield className="w-5 h-5 text-white" />
                </div>
                <div>
                  <span className="font-bold text-lg text-white">AG-12 Protocol</span>
                  <p className="text-[11px] text-[#DCE7F5]/70">PR Agent Workspace</p>
                </div>
              </div>
              <button 
                onClick={() => setMobileMenuOpen(false)}
                className="p-1.5 rounded-lg hover:bg-[#1C3B65] text-[#DCE7F5] cursor-pointer"
                aria-label="Close menu"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Mobile Nav Tabs */}
            <nav 
              className="py-4 space-y-1.5 flex-1 overflow-y-auto"
              role="tablist"
              aria-label="Mobile Navigation Tabs"
            >
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    id={`mobile-nav-${item.id}`}
                    role="tab"
                    aria-selected={isActive}
                    aria-controls={`panel-${item.id}`}
                    onClick={() => handleNavClick(item.id)}
                    className={`w-full flex items-center space-x-3 px-3.5 py-3 rounded-xl text-sm font-semibold transition-all cursor-pointer text-left ${
                      isActive
                        ? 'bg-[#DCE7F5] text-[#142B4A] shadow-sm font-bold'
                        : 'text-[#DCE7F5]/80 hover:text-white hover:bg-[#1C3B65]'
                    }`}
                  >
                    <Icon className={`w-4 h-4 ${isActive ? 'text-[#142B4A]' : 'text-[#DCE7F5]'}`} />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </nav>

            {/* Mobile Tools & Gateway */}
            <div className="pt-4 border-t border-[#1C3B65] space-y-2 text-xs">
              <button
                onClick={() => { onOpenDocs(); setMobileMenuOpen(false); }}
                className="w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-[#DCE7F5] hover:text-white hover:bg-[#1C3B65] font-semibold cursor-pointer"
              >
                <BookOpen className="w-4 h-4" />
                <span>Documentation</span>
              </button>

              <button
                onClick={() => { onOpenBenchmark(); setMobileMenuOpen(false); }}
                className="w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-[#DCE7F5] hover:text-white hover:bg-[#1C3B65] font-semibold cursor-pointer"
              >
                <Zap className="w-4 h-4 text-amber-300" />
                <span>Benchmark Suite</span>
              </button>

              <button
                onClick={() => { onOpenSettings(); setMobileMenuOpen(false); }}
                className="w-full flex items-center justify-between p-2.5 rounded-xl bg-[#1C3B65] text-[#DCE7F5] hover:text-white cursor-pointer mt-2"
              >
                <div className="flex items-center space-x-2">
                  <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-[#10B981]' : 'bg-[#F59E0B]'}`} />
                  <span className="font-bold text-white">{provider}</span>
                  <span className="text-[10px] text-[#DCE7F5]/80">({model})</span>
                </div>
                <Settings className="w-4 h-4 text-[#DCE7F5]" />
              </button>
            </div>

          </div>
        </div>
      )}

      {/* =========================================================================
          DESKTOP NAVY SIDEBAR (Fixed on lg and above screens)
          ========================================================================= */}
      <aside 
        className="hidden lg:flex lg:flex-col lg:w-64 xl:w-72 lg:fixed lg:inset-y-0 lg:z-30 bg-[#142B4A] text-white border-r border-[#1C3B65] select-none"
        aria-label="Sidebar Navigation"
      >
        
        {/* Sidebar Brand Header */}
        <div className="p-6 border-b border-[#1C3B65]">
          <button
            onClick={() => setActiveTab('studio')}
            className="flex items-start space-x-3 text-left group cursor-pointer focus:outline-none"
            aria-label="AG-12 Protocol Home - Navigate to Code Studio"
          >
            <div className="w-11 h-11 rounded-xl bg-[#1C3B65] group-hover:bg-[#264B7D] text-white flex items-center justify-center shadow-md transition-colors shrink-0">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xl font-extrabold tracking-tight text-white leading-tight">
                  AG-12
                </span>
                <span className="px-2 py-0.5 text-[10px] font-mono font-bold tracking-wider uppercase rounded-md bg-[#E9E2F5] text-[#4A2E7A] border border-[#D7C7ED]">
                  PR Agent
                </span>
              </div>
              <p className="text-xs text-[#DCE7F5]/80 font-medium mt-0.5 leading-snug">
                Autonomous Code Review
              </p>
            </div>
          </button>
        </div>

        {/* Sidebar Navigation Items */}
        <div className="flex-1 px-4 py-6 overflow-y-auto space-y-6">
          
          <div>
            <span className="px-3 text-[11px] font-bold uppercase tracking-wider text-[#DCE7F5]/60 font-mono block mb-2">
              Workspace
            </span>

            <nav 
              className="space-y-1"
              role="tablist"
              aria-label="Main Navigation Tabs"
            >
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    id={`nav-${item.id}`}
                    role="tab"
                    aria-selected={isActive}
                    aria-controls={`panel-${item.id}`}
                    onClick={() => setActiveTab(item.id)}
                    className={`w-full flex items-center space-x-3 px-3.5 py-3 rounded-xl text-sm font-semibold transition-all cursor-pointer text-left ${
                      isActive
                        ? 'bg-[#DCE7F5] text-[#142B4A] shadow-md font-bold'
                        : 'text-[#DCE7F5]/80 hover:text-white hover:bg-[#1C3B65]'
                    }`}
                  >
                    <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-[#142B4A]' : 'text-[#DCE7F5]'}`} />
                    <div className="flex-1 min-w-0">
                      <div className="truncate">{item.label}</div>
                    </div>
                    {isActive && (
                      <span className="w-1.5 h-1.5 rounded-full bg-[#142B4A] shrink-0" aria-hidden="true" />
                    )}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Quick Tools Section */}
          <div className="pt-2">
            <span className="px-3 text-[11px] font-bold uppercase tracking-wider text-[#DCE7F5]/60 font-mono block mb-2">
              System Tools
            </span>

            <div className="space-y-1 text-sm font-medium">
              <button
                onClick={onOpenDocs}
                className="w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-[#DCE7F5]/80 hover:text-white hover:bg-[#1C3B65] transition-colors cursor-pointer text-left"
                title="System Specifications and Documentation"
              >
                <BookOpen className="w-4 h-4 text-[#DCE7F5]" />
                <span>Documentation</span>
              </button>

              <button
                onClick={onOpenBenchmark}
                className="w-full flex items-center space-x-3 px-3.5 py-2.5 rounded-xl text-[#DCE7F5]/80 hover:text-white hover:bg-[#1C3B65] transition-colors cursor-pointer text-left"
                title="Launch Semantic Retrieval Benchmark Suite"
              >
                <Zap className="w-4 h-4 text-amber-300" />
                <span>Benchmark Suite</span>
              </button>
            </div>
          </div>

        </div>

        {/* Sidebar Footer: LLM Gateway Capsule */}
        <div className="p-4 border-t border-[#1C3B65] bg-[#0E1F36]/50">
          <button
            type="button"
            onClick={onOpenSettings}
            aria-label={`LLM Gateway settings: ${provider} ${model}, status ${status}`}
            className="w-full flex items-center justify-between p-3 rounded-xl bg-[#1C3B65] hover:bg-[#264B7D] border border-[#264B7D] transition-all cursor-pointer text-left group shadow-xs"
            title="Configure LLM Gateway, providers, and failover parameters"
          >
            <div className="flex items-center space-x-2.5 min-w-0">
              <span className="relative flex h-2.5 w-2.5 shrink-0" aria-hidden="true">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                  isConnected ? 'bg-emerald-400' : 'bg-amber-400'
                }`} />
                <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                  isConnected ? 'bg-[#10B981]' : 'bg-[#F59E0B]'
                }`} />
              </span>

              <div className="min-w-0">
                <div className="flex items-center space-x-1.5">
                  <span className="text-xs font-bold text-white truncate">
                    {provider}
                  </span>
                  {isFallbackActive && (
                    <span className="text-[9px] font-mono px-1 py-0.2 rounded font-bold uppercase bg-[#FEF3C7] text-[#92400E]">
                      fb
                    </span>
                  )}
                </div>
                <p className="text-[11px] font-mono text-[#DCE7F5]/70 truncate">
                  {model}
                </p>
              </div>
            </div>

            <Settings className="w-4 h-4 text-[#DCE7F5] group-hover:text-white group-hover:rotate-45 transition-all duration-200 shrink-0" />
          </button>

          <div className="mt-3 px-1 flex items-center justify-between text-[11px] text-[#DCE7F5]/50 font-mono">
            <span>AG-12 Engine</span>
            <span>v1.0.0</span>
          </div>
        </div>

      </aside>
    </>
  );
}

export default memo(Header);
