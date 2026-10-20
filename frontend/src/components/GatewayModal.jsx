import React, { useState } from 'react';
import { X, Server, Key, ShieldCheck, Cpu, CheckCircle, AlertTriangle, Info, CheckCircle2 } from 'lucide-react';
import { configureGateway } from '../services/api';

export default function GatewayModal({ isOpen, onClose, gatewayStatus, onUpdate }) {
  if (!isOpen) return null;

  const [geminiKey, setGeminiKey] = useState('');
  const [groqKey, setGroqKey] = useState('');
  const [provider, setProvider] = useState(gatewayStatus?.provider?.toLowerCase() || 'gemini');
  const [geminiModel, setGeminiModel] = useState(gatewayStatus?.model?.startsWith('gemini') ? gatewayStatus.model : 'gemini-1.5-flash');
  const [groqModel, setGroqModel] = useState(gatewayStatus?.model?.includes('llama') ? gatewayStatus.model : 'llama-3.3-70b-versatile');
  const [ollamaModel, setOllamaModel] = useState(gatewayStatus?.model?.includes('qwen') ? gatewayStatus.model : 'qwen2.5-coder:7b');
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [showVramGuidance, setShowVramGuidance] = useState(false);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        provider: provider,
        gemini_api_key: geminiKey ? geminiKey.trim() : undefined,
        groq_api_key: groqKey ? groqKey.trim() : undefined,
        gemini_model: geminiModel,
        groq_model: groqModel,
        ollama_model: ollamaModel
      };

      const updated = await configureGateway(payload);
      if (onUpdate) onUpdate(updated);
      setSavedSuccess(true);
      setTimeout(() => {
        setSavedSuccess(false);
        onClose();
      }, 1200);
    } catch (err) {
      alert(`Config update error: ${err.message}`);
    } finally {
      setSaving(false);
    }
  };

  const isOllamaUp = gatewayStatus?.ollama_available;
  const isOllamaModelReady = gatewayStatus?.ollama_model_installed;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#0E1F36]/50 backdrop-blur-xs animate-in fade-in">
      <div className="dev-card max-w-lg w-full shadow-2xl overflow-hidden border border-[#E2E6EC] bg-white">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between p-4 border-b border-[#1C3B65] bg-[#142B4A] text-white">
          <div className="flex items-center space-x-2.5">
            <Server className="w-4 h-4 text-[#DCE7F5]" />
            <h3 className="text-sm font-bold text-white">LLM Gateway &amp; Provider Configuration</h3>
          </div>
          <button
            onClick={onClose}
            className="text-[#DCE7F5] hover:text-white transition-colors cursor-pointer p-1 rounded-md hover:bg-[#1C3B65]"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSave} className="p-5 space-y-4 max-h-[85vh] overflow-y-auto bg-white">
          
          {/* Active Provider Selector */}
          <div>
            <label className="block text-xs font-semibold text-[#606973] uppercase tracking-wider mb-1.5">
              Primary Gateway Provider
            </label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="w-full bg-[#F8FAFC] border border-[#E2E6EC] rounded-xl px-3 py-2 text-xs text-[#343A40] focus:outline-none focus:border-[#142B4A] font-mono"
            >
              <option value="gemini">Google Gemini Cloud API</option>
              <option value="groq">Groq Cloud API</option>
              <option value="ollama">Local Ollama Model (Air-Gapped)</option>
              <option value="offline">Heuristic Deterministic Engine (Offline / Zero-Config)</option>
            </select>
          </div>

          {/* Conditional Model Configuration */}
          {provider === 'gemini' && (
            <div className="space-y-3 p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E6EC]">
              <div>
                <label className="block text-[11px] font-mono text-[#606973] mb-1">
                  Gemini Model Target:
                </label>
                <select
                  value={geminiModel}
                  onChange={(e) => setGeminiModel(e.target.value)}
                  className="w-full bg-white border border-[#E2E6EC] rounded-lg px-2.5 py-1.5 text-xs text-[#343A40] font-mono focus:outline-none focus:border-[#142B4A]"
                >
                  <option value="gemini-1.5-flash">gemini-1.5-flash (Fast, Low Latency)</option>
                  <option value="gemini-2.0-flash">gemini-2.0-flash (Latest General Availability)</option>
                  <option value="gemini-1.5-pro">gemini-1.5-pro (High Reasoning Depth)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-[#606973] mb-1">
                  Gemini API Key:
                </label>
                <div className="relative">
                  <input
                    type="password"
                    placeholder={gatewayStatus?.has_gemini_key ? "•••••••••••••••• (Active Key Stored)" : "AIzaSy..."}
                    value={geminiKey}
                    onChange={(e) => setGeminiKey(e.target.value)}
                    className="w-full bg-white border border-[#E2E6EC] rounded-lg px-2.5 py-1.5 text-xs text-[#343A40] font-mono focus:outline-none focus:border-[#142B4A] pr-8"
                  />
                  <Key className="w-3.5 h-3.5 text-[#606973] absolute right-2.5 top-2" />
                </div>
                <p className="text-[10px] text-[#606973] mt-1">
                  Credentials are read server-side and never exposed to the client browser.
                </p>
              </div>
            </div>
          )}

          {provider === 'groq' && (
            <div className="space-y-3 p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E6EC]">
              <div>
                <label className="block text-[11px] font-mono text-[#606973] mb-1">
                  Groq Model Target:
                </label>
                <select
                  value={groqModel}
                  onChange={(e) => setGroqModel(e.target.value)}
                  className="w-full bg-white border border-[#E2E6EC] rounded-lg px-2.5 py-1.5 text-xs text-[#343A40] font-mono focus:outline-none focus:border-[#142B4A]"
                >
                  <option value="llama-3.3-70b-versatile">llama-3.3-70b-versatile (Recommended)</option>
                  <option value="llama-3.1-8b-instant">llama-3.1-8b-instant (Ultra Fast)</option>
                  <option value="mixtral-8x7b-32768">mixtral-8x7b-32768 (MoE Architecture)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-mono text-[#606973] mb-1">
                  Groq API Key:
                </label>
                <div className="relative">
                  <input
                    type="password"
                    placeholder={gatewayStatus?.has_groq_key ? "•••••••••••••••• (Active Key Stored)" : "gsk_..."}
                    value={groqKey}
                    onChange={(e) => setGroqKey(e.target.value)}
                    className="w-full bg-white border border-[#E2E6EC] rounded-lg px-2.5 py-1.5 text-xs text-[#343A40] font-mono focus:outline-none focus:border-[#142B4A] pr-8"
                  />
                  <Key className="w-3.5 h-3.5 text-[#606973] absolute right-2.5 top-2" />
                </div>
              </div>
            </div>
          )}

          {provider === 'ollama' && (
            <div className="space-y-3 p-3.5 rounded-xl bg-[#F8FAFC] border border-[#E2E6EC]">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="block text-[11px] font-mono text-[#606973]">
                    Ollama Model Selection:
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowVramGuidance(!showVramGuidance)}
                    className="text-[10px] text-[#142B4A] hover:underline flex items-center space-x-1 cursor-pointer font-semibold"
                  >
                    <Info className="w-3 h-3" />
                    <span>4 GB VRAM Profile</span>
                  </button>
                </div>
                <select
                  value={ollamaModel}
                  onChange={(e) => setOllamaModel(e.target.value)}
                  className="w-full bg-white border border-[#E2E6EC] rounded-lg px-2.5 py-1.5 text-xs text-[#343A40] font-mono focus:outline-none focus:border-[#142B4A]"
                >
                  <option value="qwen2.5-coder:7b">qwen2.5-coder:7b (High precision; partial GPU offload)</option>
                  <option value="qwen2.5-coder:1.5b">qwen2.5-coder:1.5b (100% inside 4GB VRAM)</option>
                  <option value="qwen2.5-coder:3b">qwen2.5-coder:3b (Fits in 4GB VRAM)</option>
                  <option value="deepseek-coder:6.7b">deepseek-coder:6.7b</option>
                </select>
              </div>

              {/* Verified Status of Ollama */}
              <div className="flex items-center justify-between text-[11px] font-mono pt-1">
                <span className="text-[#606973]">Daemon Connectivity:</span>
                <span className={isOllamaUp ? 'text-[#1B5E36] font-bold' : 'text-[#991B1B] font-bold'}>
                  {isOllamaUp ? 'Online (http://localhost:11434)' : 'Offline'}
                </span>
              </div>
              <div className="flex items-center justify-between text-[11px] font-mono">
                <span className="text-[#606973]">Model Installation:</span>
                <span className={isOllamaModelReady ? 'text-[#1B5E36] font-bold' : 'text-[#92400E] font-bold'}>
                  {isOllamaModelReady ? 'Installed & Ready' : 'Not Downloaded (Auto-download disabled)'}
                </span>
              </div>

              {/* 4GB VRAM Guidance Box */}
              {showVramGuidance && (
                <div className="mt-2 p-3 rounded-lg bg-[#DCE7F5] border border-[#B8D0EC] text-[11px] space-y-1.5 text-[#142B4A]">
                  <div className="font-bold text-[#142B4A]">4 GB VRAM Constraint &amp; Sizing Matrix:</div>
                  <ul className="space-y-1 pl-3 list-disc text-[10px]">
                    <li><strong>1.5B (Q4_K_M):</strong> ~1.6 GB VRAM. 100% fits in 4GB VRAM.</li>
                    <li><strong>3B (Q4_K_M):</strong> ~2.8 GB VRAM. 100% fits in 4GB VRAM.</li>
                    <li><strong>7B (Q4_K_M):</strong> ~5.4 GB VRAM with 4K context. On a 4GB GPU, Ollama offloads ~22 layers to GPU and remaining layers to System RAM.</li>
                    <li><strong>Context Window:</strong> Kept at 2048 tokens to minimize KV cache memory overhead.</li>
                  </ul>
                </div>
              )}
            </div>
          )}

          {provider === 'offline' && (
            <div className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E6EC] text-xs text-[#343A40] space-y-1.5 leading-relaxed">
              <div className="flex items-center space-x-1.5 text-[#142B4A] font-semibold text-[11px]">
                <ShieldCheck className="w-3.5 h-3.5 text-[#142B4A]" />
                <span>Zero-Dependency Heuristic Engine</span>
              </div>
              <p className="text-[11px] text-[#606973]">
                Operates 100% offline with zero cloud or GPU requirement. Synthesizes findings using deterministic AST static rules and RAG normative guidance.
              </p>
            </div>
          )}

          {/* Telemetry Snapshot */}
          <div className="rounded-xl p-3 space-y-1.5 text-[11px] font-mono bg-[#F8FAFC] border border-[#E2E6EC]">
            <div className="flex justify-between text-[#606973]">
              <span>Verified Status:</span>
              <span className="text-[#1B5E36] font-bold">{gatewayStatus?.status || 'Connected'}</span>
            </div>
            <div className="flex justify-between text-[#606973]">
              <span>Operational Mode:</span>
              <span className="text-[#4A2E7A] font-semibold">{gatewayStatus?.operation_mode || 'PRIMARY_CLOUD'}</span>
            </div>
            <div className="flex justify-between text-[#606973]">
              <span>Failover State:</span>
              <span className={gatewayStatus?.fallback_active ? 'text-[#92400E] font-bold' : 'text-[#606973]'}>
                {gatewayStatus?.fallback_state || 'fallback: standby'}
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end space-x-2 pt-2 border-t border-[#E2E6EC]">
            <button
              type="button"
              onClick={onClose}
              className="dev-btn-secondary px-3.5 py-1.5 text-xs font-semibold"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="dev-btn-primary px-4 py-1.5 text-xs font-semibold uppercase tracking-wider flex items-center space-x-1.5"
            >
              {savedSuccess ? (
                <>
                  <CheckCircle className="w-3.5 h-3.5 text-white" />
                  <span>Saved!</span>
                </>
              ) : (
                <span>{saving ? 'Applying...' : 'Apply Configuration'}</span>
              )}
            </button>
          </div>

        </form>

      </div>
    </div>
  );
}
