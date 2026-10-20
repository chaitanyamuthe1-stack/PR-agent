import React, { useState, useMemo, useEffect, memo } from 'react';
import { 
  AlertTriangle, CheckCircle2, Bookmark, Eye, 
  Info, ChevronDown, ChevronUp, Search, ShieldCheck, 
  Terminal, Bot, ArrowUpDown, Filter
} from 'lucide-react';
import IssueDetailsModal from './IssueDetailsModal';

function IssueList({
  issues = [],
  filename = 'source_code.txt',
  onSelectLine = null,
  onToggleIgnore = null
}) {
  const [filter, setFilter] = useState('all');
  const [sortBy, setSortBy] = useState('severity');
  const [selectedIssueForModal, setSelectedIssueForModal] = useState(null);
  const [expandedIds, setExpandedIds] = useState(new Set());
  const [searchFilter, setSearchFilter] = useState('');
  
  // Bounded output rendering to preserve browser responsiveness (25 findings initial bound)
  const [visibleCount, setVisibleCount] = useState(25);

  useEffect(() => {
    setVisibleCount(25);
  }, [filter, sortBy, searchFilter]);

  const handleToggleExpand = (id) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleIgnoreClick = (issue, issueId) => {
    const isCurrentlyIgnored = Boolean(issue.ignored);
    const msg = isCurrentlyIgnored
      ? `Restore finding #${issueId} to active actionable status?`
      : `Ignore finding #${issueId}? It will be excluded from the actionable defect count.`;
    
    if (window.confirm(msg)) {
      if (onToggleIgnore) {
        onToggleIgnore(issueId);
      }
    }
  };

  // Pre-calculate count breakdowns
  const counts = useMemo(() => {
    return {
      all: issues.length,
      critical: issues.filter(i => (i.severity || '').toLowerCase() === 'critical').length,
      high: issues.filter(i => (i.severity || '').toLowerCase() === 'high').length,
      medium: issues.filter(i => (i.severity || '').toLowerCase() === 'medium').length,
      low: issues.filter(i => (i.severity || '').toLowerCase() === 'low' || (i.severity || '').toLowerCase() === 'informational').length,
      security: issues.filter(i => (i.category || '').toLowerCase() === 'security').length,
      bug: issues.filter(i => (i.category || '').toLowerCase() === 'bug').length,
      unresolved: issues.filter(i => !i.resolved && !i.ignored).length,
      resolved: issues.filter(i => i.resolved).length,
    };
  }, [issues]);

  // Filter and sort issues
  const filteredAndSortedIssues = useMemo(() => {
    let result = issues.filter(issue => {
      const sev = (issue.severity || '').toLowerCase();
      const cat = (issue.category || '').toLowerCase();

      let matchesTab = true;
      if (filter === 'all') matchesTab = true;
      else if (filter === 'critical') matchesTab = (sev === 'critical');
      else if (filter === 'high') matchesTab = (sev === 'high');
      else if (filter === 'medium') matchesTab = (sev === 'medium');
      else if (filter === 'low') matchesTab = (sev === 'low' || sev === 'informational');
      else if (filter === 'security') matchesTab = (cat === 'security');
      else if (filter === 'bug') matchesTab = (cat === 'bug');
      else if (filter === 'unresolved') matchesTab = (!issue.resolved && !issue.ignored);
      else if (filter === 'resolved') matchesTab = issue.resolved;

      if (!matchesTab) return false;

      if (searchFilter.trim()) {
        const q = searchFilter.toLowerCase();
        const titleMatch = (issue.title || '').toLowerCase().includes(q);
        const descMatch = (issue.description || '').toLowerCase().includes(q);
        const ruleMatch = (issue.rule_citation || issue.rule_id || '').toLowerCase().includes(q);
        const cweMatch = (issue.cwe || '').toLowerCase().includes(q);
        const sourceMatch = (issue.detection_source || issue.tool || '').toLowerCase().includes(q);
        return titleMatch || descMatch || ruleMatch || cweMatch || sourceMatch;
      }

      return true;
    });

    // Sorting
    const sevWeight = { critical: 0, high: 1, medium: 2, low: 3, informational: 4 };
    result.sort((a, b) => {
      if (sortBy === 'severity') {
        const weightA = sevWeight[(a.severity || '').toLowerCase()] ?? 2;
        const weightB = sevWeight[(b.severity || '').toLowerCase()] ?? 2;
        if (weightA !== weightB) return weightA - weightB;
        return (a.line || 1) - (b.line || 1);
      } else if (sortBy === 'line_asc') {
        return (a.line || 1) - (b.line || 1);
      } else if (sortBy === 'line_desc') {
        return (b.line || 1) - (a.line || 1);
      } else if (sortBy === 'category') {
        return (a.category || '').localeCompare(b.category || '');
      }
      return 0;
    });

    return result;
  }, [issues, filter, searchFilter, sortBy]);

  const getSeverityStyle = (sev) => {
    switch ((sev || '').toLowerCase()) {
      case 'critical':
        return 'bg-[#FEE2E2] text-[#991B1B] border-[#FECACA]';
      case 'high':
        return 'bg-[#FFEDD5] text-[#9A3412] border-[#FED7AA]';
      case 'medium':
        return 'bg-[#FEF9C3] text-[#854D0E] border-[#FEF08A]';
      case 'low':
        return 'bg-[#F3F5F8] text-[#343A40] border-[#E2E6EC]';
      case 'informational':
        return 'bg-[#DCE7F5] text-[#142B4A] border-[#B8D0EC]';
      default:
        return 'bg-[#F3F5F8] text-[#606973] border-[#E2E6EC]';
    }
  };

  const getCategoryStyle = (cat) => {
    switch ((cat || '').toLowerCase()) {
      case 'security':
        return 'bg-[#FEE2E2] text-[#991B1B] border-[#FECACA]';
      case 'bug':
        return 'bg-[#FFEDD5] text-[#9A3412] border-[#FED7AA]';
      case 'style':
      case 'quality':
      case 'defect':
        return 'bg-[#DCE7F5] text-[#142B4A] border-[#B8D0EC]';
      case 'performance':
        return 'bg-[#DDF2E5] text-[#1B5E36] border-[#C4E7D0]';
      case 'reliability':
      case 'complexity':
        return 'bg-[#E9E2F5] text-[#4A2E7A] border-[#D7C7ED]';
      default:
        return 'bg-[#F3F5F8] text-[#606973] border-[#E2E6EC]';
    }
  };

  const filterTabs = [
    { id: 'all', label: 'All', count: counts.all },
    { id: 'critical', label: 'Critical', count: counts.critical },
    { id: 'high', label: 'High', count: counts.high },
    { id: 'medium', label: 'Medium', count: counts.medium },
    { id: 'low', label: 'Low', count: counts.low },
    { id: 'security', label: 'Security', count: counts.security },
    { id: 'bug', label: 'Bugs', count: counts.bug },
    { id: 'unresolved', label: 'Unresolved', count: counts.unresolved },
  ];

  return (
    <div className="dev-card p-6 sm:p-7 shadow-sm space-y-6 bg-white border border-[#E2E6EC]">
      
      {/* Header Bar, Search & Sort Controls */}
      <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between pb-4 border-b border-[#E2E6EC] gap-4">
        <div>
          <div className="flex items-center space-x-3">
            <span className="w-3 h-3 rounded-full bg-[#142B4A]" />
            <h3 className="text-lg sm:text-xl font-bold text-[#142B4A] tracking-tight">
              Findings &amp; Security Review
            </h3>
          </div>
          <p className="text-xs sm:text-sm text-[#606973] mt-1">
            Standardized defect schema with verified static findings and AI security triage.
          </p>
        </div>

        {/* Search & Sort Controls */}
        <div className="flex flex-wrap items-center gap-3 w-full xl:w-auto">
          {/* Search input */}
          <div className="relative flex-1 sm:w-64">
            <Search className="w-4 h-4 text-[#606973] absolute left-3.5 top-3" />
            <input
              type="text"
              placeholder="Search issues, rules, CWE..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full bg-[#F8FAFC] border border-[#E2E6EC] rounded-xl pl-10 pr-3.5 py-2 text-xs sm:text-sm text-[#343A40] placeholder-[#606973] focus:outline-none focus:border-[#142B4A] transition-colors"
            />
          </div>

          {/* Sort By Dropdown */}
          <div className="flex items-center space-x-2 bg-[#F8FAFC] border border-[#E2E6EC] rounded-xl px-3 py-2 text-xs sm:text-sm text-[#343A40]">
            <ArrowUpDown className="w-4 h-4 text-[#142B4A] shrink-0" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="bg-transparent text-xs sm:text-sm text-[#343A40] focus:outline-none cursor-pointer"
            >
              <option value="severity">Severity (High→Low)</option>
              <option value="line_asc">Line (Ascending)</option>
              <option value="line_desc">Line (Descending)</option>
              <option value="category">Category</option>
            </select>
          </div>
        </div>
      </div>

      {/* Simplified Filter Tabs Bar */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-1 scrollbar-thin">
        {filterTabs.map(tab => {
          const isActive = filter === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setFilter(tab.id)}
              className={`px-3.5 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all shrink-0 cursor-pointer ${
                isActive
                  ? 'bg-[#142B4A] text-white shadow-sm border border-[#0E1F36]'
                  : 'bg-[#F3F5F8] text-[#606973] hover:text-[#142B4A] hover:bg-[#E2E6EC] border border-[#E2E6EC]'
              }`}
            >
              {tab.label} <span className="text-xs font-mono ml-1.5 opacity-80">({tab.count})</span>
            </button>
          );
        })}
      </div>

      {/* Issue Card Stack */}
      <div className="space-y-4" role="list" aria-label="Issue findings list">
        {issues.length === 0 ? (
          <div className="dev-subcard p-12 text-center space-y-3 rounded-xl bg-[#F8FAFC] border border-[#E2E6EC]">
            <ShieldCheck className="w-12 h-12 text-[#606973] mx-auto opacity-60" aria-hidden="true" />
            <p className="text-base font-bold text-[#142B4A]">
              Awaiting Code Review &amp; Defect Telemetry
            </p>
            <p className="text-sm text-[#606973] max-w-md mx-auto">
              Upload source code or select a language benchmark sample, then click "Run Code Review" to generate full traceable issue telemetry.
            </p>
          </div>
        ) : filteredAndSortedIssues.length === 0 ? (
          <div className="dev-subcard p-12 text-center space-y-3 rounded-xl bg-[#F8FAFC] border border-[#E2E6EC]">
            <Filter className="w-10 h-10 text-[#F59E0B] mx-auto opacity-80" aria-hidden="true" />
            <p className="text-base font-bold text-[#142B4A]">
              No findings matching the "{filter}" filter.
            </p>
            <p className="text-sm text-[#606973]">
              0 of {issues.length} total findings match the current filter and search query.
            </p>
            <button
              onClick={() => { setFilter('all'); setSearchFilter(''); }}
              className="dev-btn-secondary px-4 py-2 text-xs font-semibold text-[#142B4A] cursor-pointer"
            >
              Reset Filter
            </button>
          </div>
        ) : (
          filteredAndSortedIssues.slice(0, visibleCount).map((issue, index) => {
            const issueId = issue.id || issue.finding_id || `${(issue.category || 'DEFECT').toUpperCase()}-${String(index + 1).padStart(3, '0')}`;
            const isResolved = Boolean(issue.resolved);
            const isIgnored = Boolean(issue.ignored);
            const isExpanded = expandedIds.has(issueId);
            const isVerifiedStatic = issue.verification_status === 'verified_static' || issue.verified;
            const detectionSource = issue.detection_source || issue.tool || (issue.category === 'security' ? 'security_agent' : 'bug_agent');

            return (
              <div
                key={issueId}
                role="listitem"
                className={`dev-card-interactive p-5 sm:p-6 border transition-all rounded-xl ${
                  isIgnored
                    ? 'opacity-70 border-[#E2E6EC] bg-[#F8FAFC]'
                    : isResolved
                    ? 'border-[#C4E7D0] bg-[#DDF2E5]/20'
                    : 'border-[#E2E6EC] hover:border-[#142B4A] bg-white'
                }`}
              >
                {/* Issue Header: Tags, Badges, Line, Source & Verification */}
                <div className="flex flex-wrap items-center justify-between gap-2.5">
                  <div className="flex flex-wrap items-center gap-2">
                    {/* Finding ID */}
                    <span className="px-2.5 py-1 rounded-md font-mono font-bold text-xs bg-[#F3F5F8] text-[#142B4A] border border-[#E2E6EC]">
                      #{issueId}
                    </span>

                    {/* Line Pill */}
                    {issue.line && (
                      <button
                        type="button"
                        onClick={() => onSelectLine && onSelectLine(issue.line, issue)}
                        className="px-2.5 py-1 rounded-md font-mono text-xs font-semibold bg-[#DCE7F5] hover:bg-[#C8DBF0] text-[#142B4A] border border-[#B8D0EC] cursor-pointer transition-colors"
                        title="Click to jump to line in code editor"
                      >
                        Line {issue.line}
                      </button>
                    )}

                    {/* Severity Badge */}
                    <span className={`px-2.5 py-1 rounded-md text-xs font-mono font-bold uppercase border ${getSeverityStyle(issue.severity)}`}>
                      {issue.severity || 'MEDIUM'}
                    </span>

                    {/* Category Badge */}
                    <span className={`px-2.5 py-1 rounded-md text-xs font-mono font-bold uppercase border ${getCategoryStyle(issue.category)}`}>
                      {issue.category || 'DEFECT'}
                    </span>

                    {/* CWE Badge */}
                    {issue.cwe && (
                      <span className="px-2.5 py-1 rounded-md text-xs font-mono bg-[#F3F5F8] text-[#606973] border border-[#E2E6EC]">
                        {issue.cwe.startsWith('CWE-') ? issue.cwe : `CWE-${issue.cwe}`}
                      </span>
                    )}

                    {/* Detection Source Badge */}
                    <span className="px-2.5 py-1 rounded-md text-xs font-mono text-[#606973] bg-[#F3F5F8] border border-[#E2E6EC] flex items-center space-x-1.5" title={`Source: ${detectionSource}`}>
                      {isVerifiedStatic ? <Terminal className="w-3.5 h-3.5 text-[#10B981]" aria-hidden="true" /> : <Bot className="w-3.5 h-3.5 text-[#4A2E7A]" aria-hidden="true" />}
                      <span>{detectionSource}</span>
                    </span>

                    {/* Verification Status Pill */}
                    <span className={`px-2.5 py-1 rounded-md text-xs font-mono font-semibold uppercase border ${
                      isVerifiedStatic
                        ? 'bg-[#DDF2E5] text-[#1B5E36] border-[#C4E7D0]'
                        : 'bg-[#E9E2F5] text-[#4A2E7A] border-[#D7C7ED]'
                    }`}>
                      {isVerifiedStatic ? '✓ Verified Static' : 'AI Observation'}
                    </span>

                    {/* Resolution / Ignore Status */}
                    {isIgnored ? (
                      <span className="px-2.5 py-1 rounded-md text-xs font-mono font-bold uppercase bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A] flex items-center space-x-1">
                        <AlertTriangle className="w-3.5 h-3.5 text-[#F59E0B]" aria-hidden="true" />
                        <span>IGNORED</span>
                      </span>
                    ) : isResolved ? (
                      <span className="px-2.5 py-1 rounded-md text-xs font-mono font-bold uppercase bg-[#DDF2E5] text-[#1B5E36] border-[#C4E7D0] flex items-center space-x-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-[#10B981]" aria-hidden="true" />
                        <span>RESOLVED</span>
                      </span>
                    ) : null}
                  </div>

                  {/* Rule / Citation Tag */}
                  <div className="flex items-center space-x-2 bg-[#DCE7F5] px-3 py-1.5 rounded-lg border border-[#B8D0EC] max-w-full">
                    <Bookmark className="w-4 h-4 text-[#142B4A] shrink-0" aria-hidden="true" />
                    <span className="text-xs font-mono text-[#142B4A] font-semibold truncate max-w-xs">
                      {issue.rule_citation || issue.rule_id || `CWE-${issue.cwe || 'Standard'}`}
                    </span>
                  </div>
                </div>

                {/* Title & Description */}
                <div className="mt-3.5">
                  <h4 className={`text-base sm:text-lg font-bold leading-snug ${isResolved ? 'text-[#606973] line-through' : 'text-[#142B4A]'}`}>
                    {issue.title || 'Code Defect'}
                  </h4>
                  <p className="text-sm sm:text-base text-[#343A40] mt-1.5 leading-relaxed font-sans">
                    {issue.description}
                  </p>
                </div>

                {/* Grounded Recommendation Box */}
                {issue.recommendation && (
                  <div className={`mt-3.5 border rounded-xl p-3.5 sm:p-4 text-xs sm:text-sm ${
                    isResolved ? 'bg-[#DDF2E5]/40 border-[#C4E7D0] text-[#1B5E36]' : 'bg-[#F8FAFC] border-[#E2E6EC] text-[#343A40]'
                  }`}>
                    <span className="text-xs font-mono font-bold uppercase tracking-wider text-[#142B4A] block mb-1.5">
                      RECOMMENDED REMEDIATION
                    </span>
                    <p className="font-mono leading-relaxed whitespace-pre-wrap">
                      {issue.recommendation}
                    </p>
                  </div>
                )}

                {/* Collapsible Technical Details & Analyzer Evidence */}
                {isExpanded && (
                  <div className="mt-4 pt-3.5 border-t border-[#E2E6EC] text-xs sm:text-sm font-mono text-[#606973] space-y-3">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs">
                      <div><strong className="text-[#343A40]">Detection Source:</strong> {detectionSource}</div>
                      <div><strong className="text-[#343A40]">Verification Status:</strong> {isVerifiedStatic ? 'verified_static' : 'unverified_llm_observation'}</div>
                      <div><strong className="text-[#343A40]">Rule Identifier:</strong> {issue.rule_id || 'N/A'}</div>
                      <div><strong className="text-[#343A40]">CWE Mapping:</strong> {issue.cwe ? (issue.cwe.startsWith('CWE-') ? issue.cwe : `CWE-${issue.cwe}`) : 'OWASP Guideline'}</div>
                    </div>

                    {issue.evidence && (
                      <div>
                        <strong className="text-[#142B4A] text-xs block mb-1.5">Analyzer Evidence / Triggering Condition:</strong>
                        <pre className="p-3 bg-[#F8FAFC] rounded-lg text-[#343A40] overflow-x-auto text-xs whitespace-pre-wrap leading-relaxed border border-[#E2E6EC]">
                          {issue.evidence}
                        </pre>
                      </div>
                    )}
                  </div>
                )}

                {/* Action Buttons Bar */}
                <div className="mt-4 pt-3.5 border-t border-[#E2E6EC] flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center space-x-2.5">
                    <button
                      type="button"
                      onClick={() => setSelectedIssueForModal(issue)}
                      className="dev-btn-primary px-3.5 py-1.5 text-xs font-bold uppercase cursor-pointer"
                      title="Open full issue details modal"
                      aria-label={`View full details for finding #${issueId}`}
                    >
                      <Info className="w-3.5 h-3.5" aria-hidden="true" />
                      <span>Details</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => onSelectLine && onSelectLine(issue.line || 1, issue)}
                      className="dev-btn-secondary px-3.5 py-1.5 text-xs font-bold uppercase cursor-pointer"
                      title={`Jump to line ${issue.line || 1} in editor`}
                      aria-label={`Jump to code line ${issue.line || 1}`}
                    >
                      <Eye className="w-3.5 h-3.5 text-[#142B4A]" aria-hidden="true" />
                      <span>Line {issue.line || 1}</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleToggleExpand(issueId)}
                      className="dev-btn-secondary px-3 py-1.5 text-xs font-medium cursor-pointer"
                      title="Toggle technical details"
                      aria-label="Toggle technical details"
                    >
                      {isExpanded ? (
                        <>
                          <ChevronUp className="w-3.5 h-3.5" />
                          <span>Hide Details</span>
                        </>
                      ) : (
                        <>
                          <ChevronDown className="w-3.5 h-3.5" />
                          <span>Show Evidence</span>
                        </>
                      )}
                    </button>
                  </div>

                  {/* Ignore / Restore Action */}
                  <button
                    type="button"
                    onClick={() => handleIgnoreClick(issue, issueId)}
                    className="text-xs font-medium text-[#606973] hover:text-[#142B4A] transition-colors p-1 cursor-pointer"
                    title={isIgnored ? "Restore finding to active count" : "Ignore finding"}
                  >
                    {isIgnored ? "Restore Finding" : "Ignore"}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Pagination Bar when findings exceed visibleCount */}
      {filteredAndSortedIssues.length > visibleCount && (
        <div className="flex flex-col sm:flex-row items-center justify-between p-4 rounded-xl bg-[#F8FAFC] border border-[#E2E6EC] gap-3">
          <span className="text-xs sm:text-sm text-[#606973] font-mono">
            Showing <strong className="text-[#142B4A]">{Math.min(visibleCount, filteredAndSortedIssues.length)}</strong> of <strong className="text-[#142B4A]">{filteredAndSortedIssues.length}</strong> findings
          </span>
          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={() => setVisibleCount(prev => prev + 30)}
              className="dev-btn-secondary px-4 py-2 text-xs font-semibold text-[#142B4A] cursor-pointer"
            >
              Load More (+30)
            </button>
            <button
              type="button"
              onClick={() => setVisibleCount(filteredAndSortedIssues.length)}
              className="dev-btn-secondary px-4 py-2 text-xs font-semibold text-[#343A40] cursor-pointer"
            >
              Show All ({filteredAndSortedIssues.length})
            </button>
          </div>
        </div>
      )}

      {/* Modal for In-depth Issue Investigation */}
      <IssueDetailsModal
        isOpen={Boolean(selectedIssueForModal)}
        onClose={() => setSelectedIssueForModal(null)}
        issue={selectedIssueForModal}
        filename={filename}
        onSelectLine={onSelectLine}
        onToggleIgnore={onToggleIgnore}
      />

    </div>
  );
}

export default memo(IssueList);
