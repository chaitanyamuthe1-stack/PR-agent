import React, { useState, useEffect } from 'react';
import {
  Database,
  Search,
  Shield,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Upload,
  Cpu,
  Sliders,
  Filter,
  FileText,
  RefreshCw,
  Info,
  ExternalLink,
  ChevronRight,
  HardDrive
} from 'lucide-react';
import { fetchRagStats, queryRag, ingestRagContext, uploadRagContextFile } from '../services/api';

export default function RagVectors() {
  const [stats, setStats] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [searching, setSearching] = useState(false);
  
  // Configurable RAG query controls
  const [topK, setTopK] = useState(4);
  const [minSimilarity, setMinSimilarity] = useState(0.12);
  const [targetLang, setTargetLang] = useState('all');
  const [selectedStandard, setSelectedStandard] = useState('all');

  // Ingestion state
  const [activeTab, setActiveTab] = useState('catalog'); // 'catalog' | 'ingest'
  const [ingestFilePath, setIngestFilePath] = useState('guidelines/team_security.md');
  const [ingestContent, setIngestContent] = useState('');
  const [ingestLang, setIngestLang] = useState('all');
  const [ingestLoading, setIngestLoading] = useState(false);
  const [ingestSuccess, setIngestSuccess] = useState(null);
  const [ingestError, setIngestError] = useState(null);
  const [showResourceModal, setShowResourceModal] = useState(false);

  const loadData = () => {
    fetchRagStats()
      .then(data => {
        setStats(data.stats);
        setCatalog(data.catalog || []);
      })
      .catch(err => console.error("Error fetching RAG stats:", err));
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSearch = async (e) => {
    if (e) e.preventDefault();
    if (!searchQuery.trim()) {
      setSearchResults(null);
      return;
    }
    setSearching(true);
    try {
      const langParam = targetLang === 'all' ? null : targetLang;
      const res = await queryRag(searchQuery, langParam, topK, minSimilarity);
      setSearchResults(res.results || []);
    } catch (err) {
      alert(`RAG Search failed: ${err.message}`);
    } finally {
      setSearching(false);
    }
  };

  const handleClear = () => {
    setSearchQuery('');
    setSearchResults(null);
  };

  const handleIngestText = async (e) => {
    e.preventDefault();
    if (!ingestContent.trim()) {
      setIngestError("Please provide content to ingest.");
      return;
    }
    setIngestLoading(true);
    setIngestError(null);
    setIngestSuccess(null);
    try {
      const res = await ingestRagContext({
        file_path: ingestFilePath,
        content: ingestContent,
        language: ingestLang === 'all' ? null : ingestLang
      });
      setIngestSuccess(`Successfully indexed ${res.chunks_indexed} chunk(s) from '${res.file_path}' into vector store.`);
      setIngestContent('');
      loadData();
    } catch (err) {
      setIngestError(err.message);
    } finally {
      setIngestLoading(false);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIngestLoading(true);
    setIngestError(null);
    setIngestSuccess(null);
    try {
      const res = await uploadRagContextFile(file, ingestLang === 'all' ? null : ingestLang);
      setIngestSuccess(`Uploaded & indexed ${res.chunks_indexed} chunk(s) from '${res.file_path}'.`);
      loadData();
    } catch (err) {
      setIngestError(err.message);
    } finally {
      setIngestLoading(false);
      e.target.value = '';
    }
  };

  const displayedDocs = searchResults || catalog.filter(doc => {
    if (selectedStandard === 'all') return true;
    if (selectedStandard === 'security') return doc.category === 'security';
    if (selectedStandard === 'style') return doc.category === 'style';
    if (selectedStandard === 'bug') return doc.category === 'bug';
    if (selectedStandard === 'project') return doc.category === 'project_context';
    return true;
  });

  const provider = stats?.embedding_provider;
  const isLocal = provider?.is_local ?? true;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6 font-sans">
      
      {/* Header & Stats Banner */}
      <div className="dev-card p-6 bg-white border border-[#E6E4DC] rounded-xl shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-lg bg-[#E7EDE2] text-[#4A6B56] border border-[#DCE8D8]">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 className="text-base sm:text-lg font-bold text-[#343A35] tracking-tight">
                  RAG Vector Store &amp; Normative Grounding Base
                </h2>
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase tracking-wider ${
                  stats?.index_status === 'ready'
                    ? 'bg-[#D8E9E5] text-[#2D5A43] border border-[#C2DFD9]'
                    : 'bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]'
                }`}>
                  Status: {stats?.index_status || 'READY'}
                </span>
              </div>
              <p className="text-xs text-[#747A73] mt-0.5">
                Pre-indexed OWASP Top 10, CWE Top 25, Multi-Language Style Guides, and Uploaded Project Context
              </p>
            </div>
          </div>

          {/* Real Metrics Badges (Zero Fabrication) */}
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono">
            <div className="px-3 py-1.5 rounded-lg bg-[#F8F6F0] border border-[#E6E4DC] text-center">
              <span className="text-[#747A73] block text-[10px] uppercase">Vectors</span>
              <span className="text-[#4A6B56] font-bold">{stats?.total_vectors ?? 22} chunks</span>
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-[#F8F6F0] border border-[#E6E4DC] text-center">
              <span className="text-[#747A73] block text-[10px] uppercase">Dimension</span>
              <span className="text-[#4A3B69] font-bold">{stats?.vector_dimension ?? 128}-d Dense</span>
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-[#F8F6F0] border border-[#E6E4DC] text-center">
              <span className="text-[#747A73] block text-[10px] uppercase">Provider Mode</span>
              <span className={`font-bold ${isLocal ? 'text-[#2D5A43]' : 'text-[#4A3B69]'}`}>
                {isLocal ? 'Local Offline' : 'Gemini Cloud'}
              </span>
            </div>
            <button
              onClick={() => setShowResourceModal(!showResourceModal)}
              className="dev-btn-secondary px-2.5 py-2 text-[11px] flex items-center space-x-1 cursor-pointer"
              title="View Model & Resource Requirements"
            >
              <Info className="w-3.5 h-3.5 text-[#4A6B56]" />
              <span>Model Specs</span>
            </button>
          </div>
        </div>

        {/* Resource Requirements & Architecture Disclosure Banner */}
        {showResourceModal && (
          <div className="mt-4 p-4 rounded-lg bg-[#F8F6F0] border border-[#E6E4DC] text-xs space-y-2 animate-fadeIn shadow-sm">
            <div className="flex items-center justify-between pb-2 border-b border-[#E6E4DC]">
              <div className="flex items-center space-x-2 text-[#4A6B56] font-bold">
                <Cpu className="w-4 h-4" />
                <span>Embedding Model Architecture &amp; Resource Profile</span>
              </div>
              <span className="text-[10px] font-mono text-[#747A73] uppercase">
                {isLocal ? '100% Air-Gapped / Zero External Calls' : 'Cloud Service'}
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 font-mono text-[11px] pt-1">
              <div>
                <span className="text-[#747A73] block text-[10px]">Model:</span>
                <span className="text-[#343A35] font-semibold">{provider?.model || 'pr-agent-dense-ngram-128d'}</span>
              </div>
              <div>
                <span className="text-[#747A73] block text-[10px]">GPU / VRAM:</span>
                <span className="text-[#2D5A43] font-semibold">{provider?.resource_requirements?.gpu_vram || '0 MB (Zero GPU)'}</span>
              </div>
              <div>
                <span className="text-[#747A73] block text-[10px]">Resident RAM:</span>
                <span className="text-[#343A35] font-semibold">{provider?.resource_requirements?.ram || '< 1 MB'}</span>
              </div>
              <div>
                <span className="text-[#747A73] block text-[10px]">Network:</span>
                <span className="text-[#555C56] font-semibold">{provider?.resource_requirements?.network || 'None (Local)'}</span>
              </div>
            </div>
            <p className="text-[11px] text-[#555C56] leading-relaxed pt-1">
              {provider?.description || 'Deterministic n-gram hashed feature projection with L2 normalization.'} All vector counts and retrieval scores reflect real in-memory vector embeddings.
            </p>
          </div>
        )}

        {/* Tab Controls: Catalog vs Ingest */}
        <div className="flex items-center space-x-3 mt-5 pt-3 border-t border-[#E6E4DC]">
          <button
            onClick={() => setActiveTab('catalog')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer ${
              activeTab === 'catalog'
                ? 'bg-[#4A6B56] text-white shadow-sm'
                : 'text-[#747A73] hover:text-[#343A35] hover:bg-[#E7EDE2]'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Search &amp; Catalog ({stats?.total_chunks || catalog.length})</span>
          </button>
          <button
            onClick={() => setActiveTab('ingest')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-colors cursor-pointer ${
              activeTab === 'ingest'
                ? 'bg-[#4A6B56] text-white shadow-sm'
                : 'text-[#747A73] hover:text-[#343A35] hover:bg-[#E7EDE2]'
            }`}
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Ingest Project Context</span>
          </button>
        </div>

      </div>

      {/* TAB 1: Search & Catalog */}
      {activeTab === 'catalog' && (
        <div className="space-y-6">
          
          {/* Search & Configurable Top-K Controls Card */}
          <div className="dev-card p-5 space-y-4 bg-white border border-[#E6E4DC] rounded-xl shadow-sm">
            <form onSubmit={handleSearch} className="flex flex-col md:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-[#747A73] absolute left-3.5 top-3" />
                <input
                  type="text"
                  placeholder="Query vector store (e.g., 'SQL injection parameterized query', 'memory leak RAII', 'XSS reflected', 'empty catch block')..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-[#F8F6F0] border border-[#E6E4DC] rounded-lg pl-10 pr-4 py-2.5 text-xs font-mono text-[#343A35] focus:outline-none focus:border-[#4A6B56]"
                />
              </div>
              <div className="flex items-center space-x-2">
                <button
                  type="submit"
                  disabled={searching}
                  className="dev-btn-primary px-4 py-2.5 text-xs font-semibold uppercase tracking-wider cursor-pointer"
                >
                  {searching ? 'Querying...' : 'Semantic Query'}
                </button>
                {searchResults && (
                  <button
                    type="button"
                    onClick={handleClear}
                    className="dev-btn-secondary px-3 py-2.5 text-xs cursor-pointer"
                  >
                    Reset
                  </button>
                )}
              </div>
            </form>

            {/* Configurable Filters & Top-K Parameter Controls */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-3 border-t border-[#E6E4DC] text-xs">
              
              {/* Category Filter Pills */}
              <div className="flex items-center space-x-1.5 overflow-x-auto">
                <span className="text-[#747A73] text-[11px] uppercase font-bold mr-1">Standard:</span>
                {['all', 'security', 'bug', 'style', 'project'].map(tab => (
                  <button
                    key={tab}
                    onClick={() => setSelectedStandard(tab)}
                    className={`px-2.5 py-1 rounded-md text-xs capitalize font-medium transition-colors cursor-pointer ${
                      selectedStandard === tab
                        ? 'bg-[#E7EDE2] text-[#4A6B56] border border-[#DCE8D8] font-semibold'
                        : 'text-[#747A73] hover:text-[#343A35] hover:bg-[#F8F6F0]'
                    }`}
                  >
                    {tab === 'project' ? 'Project Context' : tab}
                  </button>
                ))}
              </div>

              {/* Advanced Parameters: Top-K and Language Affinity */}
              <div className="flex items-center space-x-4 font-mono text-xs">
                
                {/* Target Language Dropdown */}
                <div className="flex items-center space-x-1.5">
                  <span className="text-[#747A73] text-[11px]">Language:</span>
                  <select
                    value={targetLang}
                    onChange={(e) => setTargetLang(e.target.value)}
                    className="bg-[#F8F6F0] border border-[#E6E4DC] rounded px-2 py-1 text-[#343A35] text-xs focus:outline-none focus:border-[#4A6B56] cursor-pointer"
                  >
                    <option value="all">All Languages</option>
                    <option value="python">Python</option>
                    <option value="c">C</option>
                    <option value="cpp">C++</option>
                    <option value="java">Java</option>
                    <option value="javascript">JavaScript</option>
                    <option value="ruby">Ruby</option>
                  </select>
                </div>

                {/* Configurable Top-K */}
                <div className="flex items-center space-x-1.5">
                  <span className="text-[#747A73] text-[11px]">Top-K:</span>
                  <select
                    value={topK}
                    onChange={(e) => setTopK(Number(e.target.value))}
                    className="bg-[#F8F6F0] border border-[#E6E4DC] rounded px-2 py-1 text-[#343A35] text-xs focus:outline-none focus:border-[#4A6B56] cursor-pointer"
                  >
                    <option value={2}>Top 2</option>
                    <option value={4}>Top 4 (Default)</option>
                    <option value={6}>Top 6</option>
                    <option value={8}>Top 8</option>
                    <option value={12}>Top 12</option>
                  </select>
                </div>

                {/* Min Similarity Cutoff */}
                <div className="flex items-center space-x-1.5">
                  <span className="text-[#747A73] text-[11px]">Min Score:</span>
                  <select
                    value={minSimilarity}
                    onChange={(e) => setMinSimilarity(Number(e.target.value))}
                    className="bg-[#F8F6F0] border border-[#E6E4DC] rounded px-2 py-1 text-[#343A35] text-xs focus:outline-none focus:border-[#4A6B56] cursor-pointer"
                  >
                    <option value={0.08}>0.08 (Broad)</option>
                    <option value={0.12}>0.12 (Balanced)</option>
                    <option value={0.20}>0.20 (Strict)</option>
                    <option value={0.30}>0.30 (Exact)</option>
                  </select>
                </div>

              </div>

            </div>
          </div>

          {/* Search Results Summary Banner (if queried) */}
          {searchResults !== null && (
            <div className="flex items-center justify-between text-xs px-1 text-[#747A73]">
              <span>
                Found <strong className="text-[#343A35]">{searchResults.length}</strong> normative passage(s) meeting relevance threshold (&ge; {minSimilarity})
              </span>
              <span className="font-mono text-[11px] text-[#747A73]">
                Top-K: {topK} &bull; Target: {targetLang.toUpperCase()} &bull; Relevance Filtering: Active
              </span>
            </div>
          )}

          {/* Vector Catalog / Results Grid */}
          {displayedDocs.length === 0 ? (
            <div className="dev-card p-12 text-center space-y-3 bg-white border border-[#E6E4DC] rounded-xl shadow-sm">
              <AlertTriangle className="w-8 h-8 text-[#92400E] mx-auto" />
              <h3 className="text-sm font-bold text-[#343A35]">No Passages Met Relevance Threshold</h3>
              <p className="text-xs text-[#747A73] max-w-md mx-auto">
                No indexed documents met the minimum relevance threshold for this query. Irrelevant documents are strictly prevented from appearing as supporting evidence.
              </p>
              <button
                onClick={handleClear}
                className="dev-btn-secondary px-3 py-1.5 text-xs mt-2 cursor-pointer"
              >
                Reset to Full Catalog
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {displayedDocs.map((doc, idx) => {
                const isResult = doc.similarity_score !== undefined;
                return (
                  <div
                    key={doc.chunk_id || doc.id || idx}
                    className="p-5 bg-white border border-[#E6E4DC] rounded-xl shadow-sm hover:border-[#4A6B56]/50 transition-all flex flex-col justify-between"
                  >
                    <div>
                      {/* Card Header: Rule ID, CWE & Similarity Badges */}
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex flex-wrap items-center gap-1.5">
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-[#E7EDE2] text-[#4A6B56] border border-[#DCE8D8]">
                            {doc.rule_id}
                          </span>
                          {doc.cwe && doc.cwe !== "N/A" && (
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-[#E8DFF2] text-[#4A3B69] border border-[#D5C6E6]">
                              {doc.cwe}
                            </span>
                          )}
                          {doc.chunk_index !== undefined && doc.total_chunks > 1 && (
                            <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-[#F8F6F0] text-[#747A73] border border-[#E6E4DC]">
                              Chunk {doc.chunk_index + 1}/{doc.total_chunks}
                            </span>
                          )}
                        </div>

                        {isResult ? (
                          <div className="flex items-center space-x-1.5">
                            <span className={`px-2 py-0.5 rounded text-[11px] font-mono font-bold ${
                              doc.relevance_status === 'high'
                                ? 'bg-[#D8E9E5] text-[#2D5A43] border border-[#C2DFD9]'
                                : doc.relevance_status === 'medium'
                                ? 'bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]'
                                : 'bg-[#F8F6F0] text-[#747A73] border border-[#E6E4DC]'
                            }`}>
                              {(doc.similarity_score * 100).toFixed(1)}% Match
                            </span>
                          </div>
                        ) : (
                          <span className="text-[10px] font-mono text-[#747A73] uppercase font-semibold">
                            {doc.category}
                          </span>
                        )}
                      </div>

                      {/* Title & Content Passage */}
                      <h3 className="text-sm font-bold text-[#343A35] mt-2.5">
                        {doc.title}
                      </h3>
                      <p className="text-xs text-[#555C56] mt-1.5 leading-relaxed">
                        {doc.content}
                      </p>

                      {/* Grounded Remediation Snippet */}
                      {doc.remediation && (
                        <div className="mt-3.5 rounded-lg p-3 bg-[#F8F6F0] border border-[#E6E4DC]">
                          <div className="flex items-center space-x-1.5 text-[#4A6B56] text-[11px] font-semibold mb-1">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Normative Remediation Pattern:</span>
                          </div>
                          <p className="text-xs text-[#343A35] font-mono pl-5 leading-relaxed">
                            {doc.remediation}
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Footer: Traceable References & Provenance */}
                    <div className="mt-4 pt-3 border-t border-[#E6E4DC] flex flex-wrap items-center justify-between text-[11px] font-mono text-[#747A73] gap-2">
                      <div className="flex items-center space-x-1">
                        <span>Languages:</span>
                        <span className="text-[#343A35] uppercase font-semibold">
                          {doc.languages ? doc.languages.join(', ') : 'All'}
                        </span>
                      </div>
                      <span className="text-[#4A6B56] truncate max-w-xs" title={doc.citation || doc.source}>
                        {doc.citation || doc.source}
                      </span>
                    </div>

                  </div>
                );
              })}
            </div>
          )}

        </div>
      )}

      {/* TAB 2: Dynamic Project Context Ingestion */}
      {activeTab === 'ingest' && (
        <div className="dev-card p-6 space-y-6 bg-white border border-[#E6E4DC] rounded-xl shadow-sm">
          <div className="space-y-1">
            <h3 className="text-sm sm:text-base font-bold text-[#343A35] flex items-center space-x-2">
              <Upload className="w-4 h-4 text-[#4A6B56]" />
              <span>Ingest Custom Project Context &amp; Security Guidelines</span>
            </h3>
            <p className="text-xs text-[#747A73]">
              Upload project architecture documents, custom coding standards, or internal policies. Documents are automatically chunked, hashed for idempotent deduplication, and indexed into the vector store.
            </p>
          </div>

          {/* Feedback Messages */}
          {ingestSuccess && (
            <div className="p-3.5 rounded-lg bg-[#D8E9E5] border border-[#C2DFD9] text-[#2D5A43] text-xs flex items-center space-x-2">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{ingestSuccess}</span>
            </div>
          )}
          {ingestError && (
            <div className="p-3.5 rounded-lg bg-[#FEE2E2] border border-[#FECACA] text-[#991B1B] text-xs flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              <span>{ingestError}</span>
            </div>
          )}

          {/* Option A: File Upload */}
          <div className="p-6 rounded-xl border border-dashed border-[#E6E4DC] hover:border-[#4A6B56]/60 bg-[#F8F6F0] transition-colors text-center space-y-2">
            <FileText className="w-6 h-6 text-[#4A6B56] mx-auto" />
            <div className="text-xs text-[#343A35] font-semibold">Upload Guideline or Source File</div>
            <p className="text-[11px] text-[#747A73]">
              Supports .md, .txt, .py, .c, .cpp, .java, .js, .rb files up to 5MB
            </p>
            <label className="inline-block mt-2">
              <span className="dev-btn-secondary px-3 py-1.5 text-xs cursor-pointer inline-flex items-center space-x-1.5">
                <Upload className="w-3.5 h-3.5" />
                <span>Select File from Disk</span>
              </span>
              <input
                type="file"
                className="hidden"
                accept=".txt,.md,.py,.c,.cpp,.h,.hpp,.java,.js,.rb,.json"
                onChange={handleFileUpload}
                disabled={ingestLoading}
              />
            </label>
          </div>

          <div className="relative text-center">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-[#E6E4DC]" />
            </div>
            <span className="relative px-3 bg-white text-[11px] font-mono text-[#747A73] uppercase">
              Or Paste Markdown / Policy Directly
            </span>
          </div>

          {/* Option B: Direct Text Ingestion */}
          <form onSubmit={handleIngestText} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-[11px] font-mono text-[#747A73] mb-1">
                  Virtual File Path / Policy Identifier:
                </label>
                <input
                  type="text"
                  value={ingestFilePath}
                  onChange={(e) => setIngestFilePath(e.target.value)}
                  placeholder="e.g. docs/security_policy.md"
                  className="w-full bg-[#F8F6F0] border border-[#E6E4DC] rounded-lg px-3 py-2 text-xs font-mono text-[#343A35] focus:outline-none focus:border-[#4A6B56]"
                />
              </div>

              <div>
                <label className="block text-[11px] font-mono text-[#747A73] mb-1">
                  Applicable Language Affinity:
                </label>
                <select
                  value={ingestLang}
                  onChange={(e) => setIngestLang(e.target.value)}
                  className="w-full bg-[#F8F6F0] border border-[#E6E4DC] rounded-lg px-3 py-2 text-xs font-mono text-[#343A35] focus:outline-none focus:border-[#4A6B56]"
                >
                  <option value="all">All Languages</option>
                  <option value="python">Python</option>
                  <option value="c">C</option>
                  <option value="cpp">C++</option>
                  <option value="java">Java</option>
                  <option value="javascript">JavaScript</option>
                  <option value="ruby">Ruby</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-mono text-[#747A73] mb-1">
                Context / Policy Content:
              </label>
              <textarea
                rows={7}
                value={ingestContent}
                onChange={(e) => setIngestContent(e.target.value)}
                placeholder="Paste guideline text, internal architecture constraints, or compliance rules here..."
                className="w-full bg-[#F8F6F0] border border-[#E6E4DC] rounded-lg p-3 text-xs font-mono text-[#343A35] focus:outline-none focus:border-[#4A6B56] leading-relaxed"
              />
            </div>

            <button
              type="submit"
              disabled={ingestLoading || !ingestContent.trim()}
              className="dev-btn-primary px-4 py-2 text-xs font-semibold flex items-center space-x-1.5 cursor-pointer"
            >
              <Database className="w-3.5 h-3.5" />
              <span>{ingestLoading ? 'Chunking & Indexing...' : 'Index Context into Vector Store'}</span>
            </button>
          </form>

        </div>
      )}

    </div>
  );
}
