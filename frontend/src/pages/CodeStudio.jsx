import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { 
  Play, Upload, Code2, Sparkles, FileCode, CheckCircle2, Terminal, Copy, 
  Check, Wrench, RefreshCw, AlertTriangle, ShieldAlert, RotateCcw, XCircle, 
  Cpu, Download, Trash2, StopCircle, Eye, FileText, RotateCcw as ResetIcon, 
  ArrowUpRight, ChevronDown, ChevronUp, Settings2, SlidersHorizontal
} from 'lucide-react';
import ReviewHeader from '../components/ReviewHeader';
import PipelineTelemetry from '../components/PipelineTelemetry';
import TriageVerdict from '../components/TriageVerdict';
import IssueList from '../components/IssueList';
import CodeDiffViewer from '../components/CodeDiffViewer';
import AuditReportSection from '../components/AuditReportSection';
import { 
  runReview, remediateCode, recheckCode, uploadSourceFile, 
  fetchSamples, fetchLanguages, getDownloadUrl, getAuditReportUrl, normalizeErrorMessage 
} from '../services/api';
import Prism from 'prismjs';
import 'prismjs/components/prism-c';
import 'prismjs/components/prism-cpp';
import 'prismjs/components/prism-java';
import 'prismjs/components/prism-python';
import 'prismjs/components/prism-javascript';
import 'prismjs/components/prism-ruby';
import 'prismjs/themes/prism.css';

const MAX_INPUT_CHARS = 250000; // Bounded source-code size (approx 5,000 lines)

const LANGUAGE_TOOLS = {
  python: ['pylint', 'bandit'],
  cpp: ['cppcheck'],
  c: ['cppcheck'],
  java: ['checkstyle'],
  javascript: ['eslint'],
  ruby: ['rubocop']
};

const EXT_TO_LANG = {
  '.py': 'python',
  '.c': 'c',
  '.h': 'c',
  '.cpp': 'cpp',
  '.cc': 'cpp',
  '.cxx': 'cpp',
  '.hpp': 'cpp',
  '.java': 'java',
  '.js': 'javascript',
  '.jsx': 'javascript',
  '.mjs': 'javascript',
  '.cjs': 'javascript',
  '.ts': 'javascript',
  '.tsx': 'javascript',
  '.rb': 'ruby'
};

const inferLanguageFromFilename = (fname) => {
  if (!fname) return null;
  const dotIndex = fname.lastIndexOf('.');
  if (dotIndex === -1) return null;
  const ext = fname.substring(dotIndex).toLowerCase();
  return EXT_TO_LANG[ext] || null;
};

export default function CodeStudio({ gatewayStatus, onOpenSettings, requestedSampleLang, onOpenBenchmark }) {
  const [language, setLanguage] = useState('python');
  const [filename, setFilename] = useState('pr_agent_test.py');
  const [code, setCode] = useState('');
  const [fileUploadInfo, setFileUploadInfo] = useState(null);
  const [samples, setSamples] = useState({});
  const [languages, setLanguages] = useState([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  
  // Asynchronous Execution States & Cancellation
  const [loadingReview, setLoadingReview] = useState(false);
  const [remediating, setRemediating] = useState(false);
  const [rechecking, setRechecking] = useState(false);
  const [reviewError, setReviewError] = useState(null);
  const [fixStateMessage, setFixStateMessage] = useState(null);
  const abortControllerRef = useRef(null);
  
  // Monotonically increasing review session ID to prevent stale responses overwriting newer sessions
  const currentSessionIdRef = useRef(0);
  
  // Single Authoritative Review State
  const [reviewState, setReviewState] = useState(null);

  // Auto-Correct from Code Check, Given File, & Upload State Tracking
  const [autoCorrectOnReview, setAutoCorrectOnReview] = useState(false);
  const [autoCorrectOnUpload, setAutoCorrectOnUpload] = useState(false);
  const [previousCodeBeforeApply, setPreviousCodeBeforeApply] = useState(null);
  const [appliedNotice, setAppliedNotice] = useState(false);

  // Unmount request cancellation cleanup
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);
  
  // Code Navigation Line Target
  const [targetedLine, setTargetedLine] = useState(null);
  const [targetedIssue, setTargetedIssue] = useState(null);

  // Editor states
  const [copiedInput, setCopiedInput] = useState(false);
  const [editorMode, setEditorMode] = useState('syntax'); // 'syntax' | 'plain'
  const [isDraggingOver, setIsDraggingOver] = useState(false);

  const fileInputRef = useRef(null);
  const autoFixFileInputRef = useRef(null);
  const editorRef = useRef(null);
  const gutterRef = useRef(null);
  const textareaRef = useRef(null);
  const preRef = useRef(null);

  const handleEditorScroll = (e) => {
    if (gutterRef.current) {
      gutterRef.current.scrollTop = e.target.scrollTop;
    }
    if (preRef.current) {
      preRef.current.scrollTop = e.target.scrollTop;
      preRef.current.scrollLeft = e.target.scrollLeft;
    }
  };

  useEffect(() => {
    if (targetedLine && textareaRef.current) {
      const lineIndex = Math.max(0, targetedLine - 1);
      const lineHeightPx = 28;
      textareaRef.current.scrollTop = lineIndex * lineHeightPx;
      if (gutterRef.current) {
        gutterRef.current.scrollTop = lineIndex * lineHeightPx;
      }
      if (preRef.current) {
        preRef.current.scrollTop = lineIndex * lineHeightPx;
      }
    }
  }, [targetedLine]);

  // Tab key indentation support & Ctrl+Enter execution shortcut
  const handleKeyDown = (e) => {
    // Keyboard Shortcut Ctrl+Enter / Cmd+Enter to execute review, Shift+Ctrl+Enter for Auto-Correct
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      if (!loadingReview && !remediating && !rechecking && code.trim()) {
        if (e.shiftKey) {
          handleAutoCorrectClick();
        } else {
          handleRunReview();
        }
      }
      return;
    }

    if (e.key === 'Tab') {
      e.preventDefault();
      const textarea = e.target;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const tabSpaces = '    ';
      
      if (e.shiftKey) {
        const before = code.substring(0, start);
        const after = code.substring(end);
        const match = before.match(/ {1,4}$/);
        if (match) {
          const removed = match[0].length;
          setCode(before.substring(0, before.length - removed) + after);
          setTimeout(() => {
            textarea.selectionStart = textarea.selectionEnd = Math.max(0, start - removed);
          }, 0);
        }
      } else {
        const newCode = code.substring(0, start) + tabSpaces + code.substring(end);
        setCode(newCode);
        setTimeout(() => {
          textarea.selectionStart = textarea.selectionEnd = start + tabSpaces.length;
        }, 0);
      }
    }
  };

  // Helper to format bytes
  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Load preset samples & language list on mount
  useEffect(() => {
    fetchSamples().then(data => {
      setSamples(data);
      if (data.python) {
        setCode(data.python.code);
        setFilename(data.python.filename || 'pr_agent_test.py');
        setFileUploadInfo({
          size: data.python.code.length,
          status: 'Sample loaded'
        });
      }
    }).catch(err => console.error("Samples load error:", err));

    fetchLanguages().then(data => {
      setLanguages(data.languages || []);
    }).catch(err => console.error("Languages load error:", err));
  }, []);

  // Filename change with automatic language inference
  const handleFilenameChange = useCallback((newFilename) => {
    setFilename(newFilename);
    const inferred = inferLanguageFromFilename(newFilename);
    if (inferred && inferred !== language) {
      setLanguage(inferred);
    }
  }, [language]);

  // Language change
  const handleLanguageChange = useCallback((newLang) => {
    setLanguage(newLang);
    const sample = samples[newLang];
    if (sample && (!code || code === samples[language]?.code)) {
      setCode(sample.code);
      setFilename(sample.filename || `sample_${newLang}`);
      setFileUploadInfo({
        size: sample.code.length,
        status: 'Sample loaded'
      });
    } else {
      const extMap = { python: '.py', cpp: '.cpp', c: '.c', java: '.java', javascript: '.js', ruby: '.rb' };
      const curExt = Object.keys(EXT_TO_LANG).find(ext => filename.endsWith(ext));
      if (curExt) {
        const base = filename.substring(0, filename.length - curExt.length);
        setFilename(`${base}${extMap[newLang] || '.txt'}`);
      }
    }
  }, [code, filename, language, samples]);

  // Load explicit sample
  const handleLoadSample = useCallback((langKey) => {
    currentSessionIdRef.current++;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setLoadingReview(false);
    setRemediating(false);
    setRechecking(false);

    const targetLang = langKey || language;
    const sample = samples[targetLang];
    if (sample) {
      setCode(sample.code);
      setFilename(sample.filename || `sample_${targetLang}`);
      setLanguage(targetLang);
      setFileUploadInfo({
        size: sample.code.length,
        status: 'Sample loaded'
      });
      setReviewState(null);
      setReviewError(null);
      setFixStateMessage(null);
      setTargetedLine(null);
      setTargetedIssue(null);
    }
  }, [language, samples]);

  // Sync sample loading when requested from Benchmark Modal or external action
  useEffect(() => {
    if (requestedSampleLang && samples[requestedSampleLang]) {
      handleLoadSample(requestedSampleLang);
    }
  }, [requestedSampleLang, samples, handleLoadSample]);

  // Cancel / Safely stop active work
  const handleCancelExecution = useCallback(() => {
    currentSessionIdRef.current++;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setLoadingReview(false);
    setRemediating(false);
    setRechecking(false);
    setReviewError("Execution safely stopped by user.");
  }, []);


  // RE-CHECK PIPELINE
  const executeRecheckPipeline = useCallback(async (origCode, corrCode, existingChangelog = null, targetSessionId = null) => {
    const thisSessionId = targetSessionId || ++currentSessionIdRef.current;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setRechecking(true);
    try {
      const recheckRes = await recheckCode({
        original_code: origCode,
        corrected_code: corrCode,
        language: reviewState?.language || language,
        filename: reviewState?.filename || filename,
        previous_issues: reviewState?.issues || [],
        provider: gatewayStatus?.provider,
        review_id: reviewState?.review_id
      }, controller.signal);

      if (thisSessionId !== currentSessionIdRef.current) return;

      const ignoredSet = new Set((reviewState?.issues || []).filter(i => i.ignored).map(i => i.id));
      const updatedIssues = (recheckRes.issues || []).map(i => ({
        ...i,
        ignored: ignoredSet.has(i.id)
      }));

      const unresolved = updatedIssues.filter(i => !i.resolved && !i.ignored);
      const resolved = updatedIssues.filter(i => i.resolved);
      const finalVerdict = unresolved.length === 0 ? 'CLEAN' : 'FIX REQUIRED';
      const postFixScore = unresolved.length === 0 ? 10.0 : (recheckRes.post_fix_score || recheckRes.health_score || 7.5);

      setReviewState(prev => {
        const initialScore = prev?.pre_fix_score ?? prev?.initial_health_score ?? prev?.health_score ?? 3.5;
        return {
          ...(prev || {}),
          ...recheckRes,
          issues: updatedIssues,
          unresolved_count: unresolved.length,
          resolved_count: resolved.length,
          pre_fix_score: initialScore,
          initial_health_score: initialScore,
          health_score: postFixScore,
          post_fix_score: postFixScore,
          verdict: finalVerdict,
          corrected_code: corrCode,
          changelog: existingChangelog || prev?.changelog || recheckRes.changelog || [],
          remediation_status: unresolved.length === 0 ? 'SUCCESS' : 'PARTIAL',
          auto_fix_failure: unresolved.length > 0
        };
      });

      setFixStateMessage(unresolved.length === 0 ? `RE-CHECK PASSED: Codebase verified CLEAN (Health Score: ${postFixScore.toFixed(1)}/10.0).` : `RE-CHECK COMPLETE: ${unresolved.length} remaining issue(s).`);
    } catch (err) {
      if (err.name === 'AbortError') {
        setReviewError("Re-check cancelled by user.");
      } else {
        setReviewError(`Re-check failed: ${normalizeErrorMessage(err)}`);
      }
    } finally {
      if (thisSessionId === currentSessionIdRef.current) {
        setRechecking(false);
        abortControllerRef.current = null;
      }
    }
  }, [filename, gatewayStatus, language, reviewState]);

  // APPLY FIX HANDLER (AUTO-CORRECT)
  const handleApplyFix = useCallback(async (customIssues = null, customReviewState = null, overrideCode = null, overrideLang = null, overrideFilename = null) => {
    if (remediating || rechecking) return;
    const activeState = customReviewState || reviewState;
    const targetCode = overrideCode !== null ? overrideCode : (activeState?.original_code || code);
    const targetLang = overrideLang !== null ? overrideLang : (activeState?.language || language);
    const targetFilename = overrideFilename !== null ? overrideFilename : (activeState?.filename || filename);

    if (!targetCode || !targetCode.trim()) {
      setReviewError("Please run a review before applying fixes.");
      return;
    }

    const currentIssues = customIssues || activeState?.issues || [];
    const actionableIssues = currentIssues.filter(i => !i.ignored && !i.resolved);

    if (actionableIssues.length === 0 && currentIssues.length > 0) {
      setFixStateMessage("All actionable issues are already resolved or ignored.");
      return;
    }

    const thisSessionId = ++currentSessionIdRef.current;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setRemediating(true);
    setReviewError(null);
    setFixStateMessage("Executing Coder Agent auto-remediation...");

    try {
      const remResult = await remediateCode({
        code: targetCode,
        language: targetLang,
        filename: targetFilename,
        issues: actionableIssues,
        provider: gatewayStatus?.provider,
        review_id: activeState?.review_id
      }, controller.signal);

      if (thisSessionId !== currentSessionIdRef.current) return;

      const wasModified = Boolean(remResult.modified && remResult.corrected_code && remResult.corrected_code.trim() !== targetCode.trim());

      if (!wasModified) {
        setFixStateMessage("Coder Agent was unable to produce automated modifications for remaining defects.");
        setReviewState(prev => prev ? ({
          ...prev,
          remediation_status: 'FAILED',
          auto_fix_failure: true,
          verdict: 'FIX REQUIRED'
        }) : null);
        return;
      }

      const newChangelog = remResult.changelog || [];
      
      await executeRecheckPipeline(
        targetCode,
        remResult.corrected_code,
        newChangelog,
        thisSessionId
      );

    } catch (err) {
      if (err.name === 'AbortError') {
        setReviewError("Fix execution cancelled by user.");
      } else {
        setReviewError(`Fix failed: ${normalizeErrorMessage(err)}`);
      }
    } finally {
      if (thisSessionId === currentSessionIdRef.current) {
        setRemediating(false);
        abortControllerRef.current = null;
      }
    }
  }, [code, executeRecheckPipeline, filename, gatewayStatus, language, remediating, rechecking, reviewState]);

  // PRIMARY ACTION: RUN CODE REVIEW (CODE CHECK) WITH INTEGRATED AUTO-CORRECT OPTION
  const handleRunReview = useCallback(async (autoFixOverride = null, overrideCode = null, overrideLang = null, overrideFilename = null) => {
    if (loadingReview || remediating || rechecking) return;
    const targetCode = overrideCode !== null ? overrideCode : code;
    const targetLang = overrideLang !== null ? overrideLang : language;
    const targetFilename = overrideFilename !== null ? overrideFilename : filename;

    if (!targetCode || !targetCode.trim()) {
      setReviewError("Source code cannot be empty. Upload a file or select a sample.");
      return;
    }

    const shouldAutoFix = autoFixOverride !== null ? autoFixOverride : autoCorrectOnReview;

    const thisSessionId = ++currentSessionIdRef.current;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setLoadingReview(true);
    setReviewError(null);
    setFixStateMessage(shouldAutoFix ? "Analyzing code and preparing auto-correction..." : null);
    setTargetedLine(null);

    try {
      const result = await runReview({
        code: targetCode,
        language: targetLang,
        filename: targetFilename,
        provider: gatewayStatus?.provider
      }, controller.signal);

      // Guard: Discard stale response
      if (thisSessionId !== currentSessionIdRef.current) {
        console.warn(`[PR Agent] Discarding stale review response from session #${thisSessionId}.`);
        return;
      }

      // Synchronize Authoritative State
      const issues = (result.issues || []).map((iss, i) => ({
        ...iss,
        id: iss.id || `${(iss.category || 'DEFECT').toUpperCase()}-${String(i + 1).padStart(3, '0')}`,
        ignored: false,
        resolved: Boolean(iss.resolved)
      }));

      const unresolved = issues.filter(i => !i.resolved && !i.ignored);
      const resolved = issues.filter(i => i.resolved);
      const verdict = unresolved.length > 0 ? 'FIX REQUIRED' : 'CLEAN';

      const initialReviewState = {
        ...result,
        issues,
        unresolved_count: unresolved.length,
        resolved_count: resolved.length,
        verdict: verdict,
        health_score: result.health_score ?? (unresolved.length > 0 ? 3.5 : 10.0),
        original_code: targetCode,
        corrected_code: result.corrected_code || targetCode,
        remediation_status: result.remediation_status || 'NOT_REQUIRED',
        auto_fix_failure: Boolean(result.auto_fix_failure)
      };

      setReviewState(initialReviewState);

      // If Auto-Correct was requested from Code Check, Given File, or Upload, immediately execute Coder Agent remediation!
      if (shouldAutoFix && unresolved.length > 0) {
        setLoadingReview(false);
        await handleApplyFix(unresolved, initialReviewState, targetCode, targetLang, targetFilename);
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        setReviewError("Review execution cancelled by user.");
      } else {
        setReviewError(`Review failed: ${normalizeErrorMessage(err)}`);
      }
    } finally {
      if (thisSessionId === currentSessionIdRef.current) {
        setLoadingReview(false);
        abortControllerRef.current = null;
      }
    }
  }, [autoCorrectOnReview, code, filename, gatewayStatus, handleApplyFix, language, loadingReview, remediating, rechecking]);

  // File Upload processor (supports immediate auto-correct for uploaded files)
  const processUploadedFile = useCallback(async (file, autoCorrect = false) => {
    if (!file) return;

    currentSessionIdRef.current++;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setLoadingReview(false);
    setRemediating(false);
    setRechecking(false);
    setReviewState(null);

    const shouldAutoFix = autoCorrect || autoCorrectOnUpload;

    try {
      const res = await uploadSourceFile(file);
      let loadedCode = res.code || '';
      if (loadedCode.length > MAX_INPUT_CHARS) {
        loadedCode = loadedCode.slice(0, MAX_INPUT_CHARS);
        setFixStateMessage(`Input bounded to ${MAX_INPUT_CHARS.toLocaleString()} characters.`);
      }
      setCode(loadedCode);
      setFilename(res.filename);
      setLanguage(res.language);
      setFileUploadInfo({
        size: file.size,
        status: shouldAutoFix ? 'Uploaded — Auto-correcting...' : 'Uploaded successfully'
      });
      setReviewError(null);

      if (shouldAutoFix) {
        setFixStateMessage(`Auto-correcting uploaded file ${res.filename}...`);
        setTimeout(() => {
          handleRunReview(true, loadedCode, res.language, res.filename);
        }, 50);
      }
    } catch (err) {
      const reader = new FileReader();
      reader.onload = (event) => {
        let text = event.target.result || '';
        if (text.length > MAX_INPUT_CHARS) {
          text = text.slice(0, MAX_INPUT_CHARS);
          setFixStateMessage(`Input bounded to ${MAX_INPUT_CHARS.toLocaleString()} characters.`);
        }
        const inferred = inferLanguageFromFilename(file.name) || 'python';
        setCode(text);
        setFilename(file.name);
        setLanguage(inferred);
        setFileUploadInfo({
          size: file.size,
          status: shouldAutoFix ? 'Loaded — Auto-correcting...' : 'Loaded local file'
        });
        setReviewError(null);

        if (shouldAutoFix) {
          setFixStateMessage(`Auto-correcting uploaded file ${file.name}...`);
          setTimeout(() => {
            handleRunReview(true, text, inferred, file.name);
          }, 50);
        }
      };
      reader.readAsText(file);
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
      if (autoFixFileInputRef.current) autoFixFileInputRef.current.value = '';
    }
  }, [autoCorrectOnUpload, handleRunReview]);

  const handleFileUpload = useCallback((e) => {
    const file = e.target.files?.[0];
    if (file) processUploadedFile(file, false);
  }, [processUploadedFile]);

  const handleAutoFixFileUpload = useCallback((e) => {
    const file = e.target.files?.[0];
    if (file) processUploadedFile(file, true);
  }, [processUploadedFile]);

  // Drag and Drop handlers (with auto-correct support)
  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(false);
  }, []);

  const handleDrop = useCallback(async (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      await processUploadedFile(file, autoCorrectOnUpload);
    }
  }, [autoCorrectOnUpload, processUploadedFile]);

  // Auto-correct the given file currently in editor
  const handleAutoCorrectFile = useCallback(() => {
    if (loadingReview || remediating || rechecking || !code.trim()) return;
    if (reviewState && reviewState.issues && reviewState.original_code === code && reviewState.unresolved_count > 0) {
      handleApplyFix();
    } else {
      handleRunReview(true, code, language, filename);
    }
  }, [code, filename, handleApplyFix, handleRunReview, language, loadingReview, rechecking, remediating, reviewState]);

  // Load a given benchmark sample and immediately auto-correct it
  const handleLoadSampleAndAutoCorrect = useCallback((langKey) => {
    const targetLang = langKey || language;
    const sample = samples[targetLang];
    if (sample) {
      currentSessionIdRef.current++;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        abortControllerRef.current = null;
      }
      setLoadingReview(false);
      setRemediating(false);
      setRechecking(false);

      const targetFilename = sample.filename || `sample_${targetLang}`;
      setCode(sample.code);
      setFilename(targetFilename);
      setLanguage(targetLang);
      setFileUploadInfo({
        size: sample.code.length,
        status: 'Sample loaded — Auto-correcting...'
      });
      setReviewState(null);
      setReviewError(null);
      setFixStateMessage(`Auto-correcting ${targetLang.toUpperCase()} given sample...`);
      setTimeout(() => {
        handleRunReview(true, sample.code, targetLang, targetFilename);
      }, 50);
    }
  }, [handleRunReview, language, samples]);

  // Dedicated Auto-Correct trigger from Code Check
  const handleAutoCorrectClick = useCallback(() => {
    if (loadingReview || remediating || rechecking) return;
    if (reviewState && reviewState.issues && reviewState.original_code === code && reviewState.unresolved_count > 0) {
      handleApplyFix();
    } else {
      handleRunReview(true);
    }
  }, [code, handleApplyFix, handleRunReview, loadingReview, rechecking, remediating, reviewState]);

  // Detect whether auto-correct has modified the code
  const hasAutoCorrectChanges = useMemo(() => {
    if (!reviewState?.corrected_code) return false;
    const origClean = (code || '').trim();
    const corrClean = reviewState.corrected_code.trim();
    return origClean !== corrClean && (
      (reviewState.changelog && reviewState.changelog.length > 0) ||
      reviewState.remediation_status === 'SUCCESS' ||
      reviewState.remediation_status === 'PARTIAL'
    );
  }, [code, reviewState]);

  // Apply auto-corrected code to editor ("after the change of auto correct")
  // Apply auto-corrected code to editor ("after the change of auto correct")
  const handleApplyToEditor = useCallback((targetCode = null) => {
    const codeToApply = targetCode || reviewState?.corrected_code;
    if (!codeToApply) return;
    const newScore = reviewState?.post_fix_score ?? reviewState?.health_score ?? 10.0;
    setPreviousCodeBeforeApply(code);
    setCode(codeToApply);
    setAppliedNotice(true);
    setFixStateMessage(`Auto-corrected code applied to editor! Health score updated to: ${newScore.toFixed(1)} / 10.0.`);
    setReviewState(prev => {
      if (!prev) return null;
      return {
        ...prev,
        original_code: codeToApply,
        health_score: newScore,
        verdict: prev.unresolved_count === 0 ? 'CLEAN' : prev.verdict,
        applied_to_editor: true
      };
    });
    setTimeout(() => setAppliedNotice(false), 6000);
  }, [code, reviewState]);

  // Revert applied code to pre-correction version
  const handleRevertAppliedCode = useCallback(() => {
    if (previousCodeBeforeApply !== null) {
      setCode(previousCodeBeforeApply);
      setReviewState(prev => {
        if (!prev) return null;
        const revertScore = prev.pre_fix_score ?? prev.initial_health_score ?? 3.5;
        return {
          ...prev,
          original_code: previousCodeBeforeApply,
          health_score: revertScore,
          applied_to_editor: false
        };
      });
      setPreviousCodeBeforeApply(null);
      setAppliedNotice(false);
      setFixStateMessage("Reverted editor code to pre-correction version.");
    }
  }, [previousCodeBeforeApply]);

  const handleManualRecheck = useCallback(() => {
    if (loadingReview || remediating || rechecking) return;
    if (!reviewState || !reviewState.corrected_code) {
      setReviewError("No corrected code available to re-check.");
      return;
    }
    executeRecheckPipeline(
      reviewState.original_code || code,
      reviewState.corrected_code,
      reviewState.changelog
    );
  }, [code, executeRecheckPipeline, loadingReview, rechecking, remediating, reviewState]);

  // IGNORE ISSUE HANDLER
  const handleToggleIgnore = useCallback((issueId) => {
    setReviewState(prev => {
      if (!prev) return null;
      const updatedIssues = prev.issues.map(iss => {
        if (iss.id === issueId) {
          return { ...iss, ignored: !iss.ignored };
        }
        return iss;
      });

      const unresolved = updatedIssues.filter(i => !i.resolved && !i.ignored);
      const resolved = updatedIssues.filter(i => i.resolved);
      const ignoredCount = updatedIssues.filter(i => i.ignored).length;
      const newVerdict = unresolved.length === 0 ? 'CLEAN' : 'FIX REQUIRED';

      return {
        ...prev,
        issues: updatedIssues,
        unresolved_count: unresolved.length,
        resolved_count: resolved.length,
        ignored_count: ignoredCount,
        verdict: newVerdict,
        post_fix_score: unresolved.length === 0 ? 10.0 : prev.post_fix_score
      };
    });
  }, []);

  // CODE NAVIGATION HANDLER
  const handleSelectLine = useCallback((line, issue = null) => {
    setTargetedLine(line);
    setTargetedIssue(issue);
    
    const elem = document.getElementById('code-remediation-panel') || editorRef.current;
    if (elem) {
      elem.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, []);

  const handleCopyInputCode = useCallback(() => {
    navigator.clipboard.writeText(code);
    setCopiedInput(true);
    setTimeout(() => setCopiedInput(false), 2000);
  }, [code]);

  // Download Source Code Action
  const handleDownloadSource = useCallback(() => {
    const codeToDownload = (reviewState && reviewState.corrected_code) ? reviewState.corrected_code : code;
    const targetName = (reviewState && reviewState.filename) ? reviewState.filename : filename;
    const blob = new Blob([codeToDownload], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = targetName || 'source_code.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [code, filename, reviewState]);

  // Download Audit Report Action
  const handleDownloadAuditReport = useCallback(() => {
    if (reviewState?.review_id) {
      const url = getAuditReportUrl(reviewState.review_id);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_report_${reviewState.review_id}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } else {
      const draft = `# PR Agent Audit Report\n\n- Filename: ${filename}\n- Language: ${language}\n- Lines: ${code ? code.split('\n').length : 0}\n- Status: Unaudited\n`;
      const blob = new Blob([draft], { type: 'text/markdown;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${filename || 'code'}_audit_report.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  }, [code, filename, language, reviewState]);

  // Reset Workspace Action
  const handleResetWorkspace = useCallback(() => {
    if (code && !window.confirm("Reset workspace? This will clear the editor and active review session.")) {
      return;
    }
    currentSessionIdRef.current++;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setLoadingReview(false);
    setRemediating(false);
    setRechecking(false);
    setCode('');
    setFilename('pr_agent_test.py');
    setLanguage('python');
    setFileUploadInfo(null);
    setReviewState(null);
    setReviewError(null);
    setFixStateMessage(null);
    setTargetedLine(null);
    setTargetedIssue(null);
  }, [code]);

  // Clear Editor Code Only
  const handleClearCode = useCallback(() => {
    setCode('');
    setFileUploadInfo(null);
  }, []);

  // Syntax highlighting HTML generator
  const highlightedCodeHtml = useMemo(() => {
    if (!code) return '';
    if (code.length > 50000 || editorMode === 'plain') {
      return code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
    const langKey = language === 'cpp' ? 'cpp' :
                    language === 'c' ? 'c' :
                    language === 'java' ? 'java' :
                    language === 'javascript' ? 'javascript' :
                    language === 'ruby' ? 'ruby' : 'python';
    const grammar = Prism.languages[langKey] || Prism.languages.clike;
    try {
      return Prism.highlight(code, grammar, langKey);
    } catch (e) {
      return code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
  }, [code, language, editorMode]);

  const activeTools = reviewState?.mcp_tools || LANGUAGE_TOOLS[language] || ['pylint'];
  const lineCount = code ? code.split('\n').length : 0;
  const isAnyExecuting = loadingReview || remediating || rechecking;

  return (
    <div className="space-y-7">
      
      {/* =========================================================================
          WORKFLOW STEP 2: CLEAR HEADING
          ========================================================================= */}
      <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-2 pb-1">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-[#142B4A] tracking-tight">
            Review your code.
          </h1>
          <p className="text-sm text-[#606973] mt-1">
            Autonomous multi-agent review, deterministic static security analysis, and grounded remediation.
          </p>
        </div>
      </div>

      {/* Global Error Banner */}
      {reviewError && (
        <div className="p-4 sm:p-5 rounded-xl bg-[#FEE2E2] border border-[#FECACA] flex items-center justify-between shadow-sm text-[#991B1B] text-sm">
          <div className="flex items-center space-x-3">
            <ShieldAlert className="w-5 h-5 text-[#EF4444] shrink-0" />
            <span className="font-semibold">{reviewError}</span>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={handleRunReview}
              disabled={isAnyExecuting}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg text-xs font-bold uppercase bg-[#EF4444] hover:bg-[#DC2626] text-white border border-[#DC2626] transition-colors cursor-pointer disabled:opacity-40"
              title="Rerun the review"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Retry</span>
            </button>
            <button
              onClick={() => setReviewError(null)}
              className="text-[#991B1B] hover:text-[#7F1D1D] p-1.5 cursor-pointer rounded-md hover:bg-[#FCD8D8]"
              title="Dismiss error"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* =========================================================================
          WORKFLOW STEP 3: CODE EDITOR WITH LANGUAGE SELECTOR & TOOLS
          ========================================================================= */}
      <div className="dev-card overflow-hidden bg-white border border-[#E2E6EC] shadow-sm">
        
        {/* Source File Controls Bar */}
        <div className="p-3.5 sm:p-4 bg-[#F8FAFC] border-b border-[#E2E6EC] flex flex-col md:flex-row md:items-center md:justify-between gap-3">
          
          {/* Left: Filename, Language, Benchmark Samples, Upload */}
          <div className="flex flex-wrap items-center gap-2.5">
            {/* Active File Tab & Input */}
            <div className="flex items-center space-x-2 bg-white border border-[#E2E6EC] hover:border-[#142B4A] px-3 py-1.5 rounded-xl transition-colors shadow-2xs">
              <FileCode className="w-4 h-4 text-[#142B4A] shrink-0" />
              <input
                type="text"
                value={filename}
                onChange={(e) => handleFilenameChange(e.target.value)}
                className="bg-transparent text-sm font-mono font-medium text-[#142B4A] focus:outline-none w-36 sm:w-48 placeholder-[#606973]"
                title="Target Filename (edit extension to auto-detect language)"
                placeholder="filename.ext"
              />
            </div>

            {/* Language Selector */}
            <div className="flex items-center bg-white border border-[#E2E6EC] rounded-xl px-3 py-1.5 shadow-2xs">
              <span className="text-xs font-semibold text-[#606973] uppercase tracking-wider mr-2">Lang</span>
              <select
                value={language}
                onChange={(e) => handleLanguageChange(e.target.value)}
                className="bg-transparent text-sm font-semibold text-[#343A40] focus:outline-none cursor-pointer"
                title="Select language"
              >
                <option value="python">Python (.py)</option>
                <option value="cpp">C++ (.cpp)</option>
                <option value="c">C (.c)</option>
                <option value="java">Java (.java)</option>
                <option value="javascript">JavaScript (.js)</option>
                <option value="ruby">Ruby (.rb)</option>
              </select>
            </div>

            {/* Benchmark Samples Selector */}
            <select
              onChange={(e) => {
                if (e.target.value) handleLoadSample(e.target.value);
              }}
              value={language}
              disabled={isAnyExecuting}
              className="bg-white border border-[#E2E6EC] hover:border-[#142B4A] text-xs sm:text-sm font-medium text-[#343A40] rounded-xl px-3 py-1.5 focus:outline-none cursor-pointer transition-colors disabled:opacity-40 shadow-2xs"
              title="Load benchmark sample"
            >
              <option value="python">Sample: Python (SQLi, Injection)</option>
              <option value="cpp">Sample: C++ (Buffer, Null Ptr)</option>
              <option value="c">Sample: C (Format, Memory Leak)</option>
              <option value="java">Sample: Java (SQLi, Secrets)</option>
              <option value="javascript">Sample: JavaScript (XSS, Eval)</option>
              <option value="ruby">Sample: Ruby (SQLi, Deserialization)</option>
            </select>

            {/* Auto-Correct Given File Button */}
            <button
              onClick={handleAutoCorrectFile}
              disabled={isAnyExecuting || !code || !code.trim()}
              className="dev-btn-secondary px-3 py-1.5 text-xs sm:text-sm font-semibold text-[#142B4A] hover:bg-[#DCE7F5] border-[#B8D0EC] cursor-pointer disabled:opacity-40 shadow-2xs flex items-center space-x-1.5"
              title="Run AI review and auto-correction on the given file in editor"
            >
              <Sparkles className="w-3.5 h-3.5 text-[#142B4A]" />
              <span>Auto-Correct File</span>
            </button>

            {/* Standard Upload Button */}
            <input
              type="file"
              ref={fileInputRef}
              accept=".py,.cpp,.c,.h,.java,.js,.jsx,.rb"
              onChange={handleFileUpload}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isAnyExecuting}
              className="dev-btn-secondary px-3 py-1.5 text-xs sm:text-sm font-medium cursor-pointer disabled:opacity-40 shadow-2xs flex items-center space-x-1.5"
              title="Upload file into editor without automatic review"
            >
              <Upload className="w-3.5 h-3.5 text-[#606973]" />
              <span>Upload</span>
            </button>

            {/* Upload & Auto-Correct Button */}
            <input
              type="file"
              ref={autoFixFileInputRef}
              accept=".py,.cpp,.c,.h,.java,.js,.jsx,.rb"
              onChange={handleAutoFixFileUpload}
              className="hidden"
            />
            <button
              onClick={() => autoFixFileInputRef.current?.click()}
              disabled={isAnyExecuting}
              className="bg-[#142B4A] hover:bg-[#1E3E6B] text-white border border-[#142B4A] px-3.5 py-1.5 rounded-xl text-xs sm:text-sm font-semibold flex items-center space-x-1.5 cursor-pointer disabled:opacity-40 shadow-xs transition-colors"
              title="Upload any file and immediately auto-correct issues with AI"
            >
              <Sparkles className="w-3.5 h-3.5 text-white" />
              <span>Upload &amp; Auto-Correct</span>
            </button>
          </div>

          {/* Right: Mode Switcher, Copy, Clear, and Expandable Settings */}
          <div className="flex items-center space-x-2 sm:space-x-3 shrink-0">
            {/* Syntax / Plain Switcher */}
            <div className="flex items-center bg-[#F3F5F8] border border-[#E2E6EC] rounded-xl p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setEditorMode('syntax')}
                className={`px-2.5 py-1 rounded-lg font-medium transition-colors cursor-pointer ${
                  editorMode === 'syntax'
                    ? 'bg-white text-[#142B4A] font-bold shadow-2xs'
                    : 'text-[#606973] hover:text-[#142B4A]'
                }`}
                title="Syntax highlighting mode"
              >
                Syntax
              </button>
              <button
                type="button"
                onClick={() => setEditorMode('plain')}
                className={`px-2.5 py-1 rounded-lg font-medium transition-colors cursor-pointer ${
                  editorMode === 'plain'
                    ? 'bg-white text-[#142B4A] font-bold shadow-2xs'
                    : 'text-[#606973] hover:text-[#142B4A]'
                }`}
                title="Plain monospace mode"
              >
                Plain
              </button>
            </div>

            {/* Copy Button */}
            <button
              onClick={handleCopyInputCode}
              className="dev-btn-secondary px-3 py-1.5 text-xs font-medium cursor-pointer"
              title="Copy code"
            >
              {copiedInput ? <Check className="w-3.5 h-3.5 text-[#10B981]" /> : <Copy className="w-3.5 h-3.5 text-[#606973]" />}
              <span>{copiedInput ? 'Copied' : 'Copy'}</span>
            </button>

            {/* Clear Button */}
            <button
              onClick={handleClearCode}
              disabled={!code}
              className="dev-btn-secondary px-3 py-1.5 text-xs font-medium text-[#606973] hover:text-[#991B1B] cursor-pointer disabled:opacity-40"
              title="Clear editor"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clear</span>
            </button>

            {/* Advanced Settings Drawer Toggle */}
            <button
              onClick={() => setShowAdvanced(!showAdvanced)}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl text-xs font-medium transition-colors border cursor-pointer ${
                showAdvanced
                  ? 'bg-[#DCE7F5] text-[#142B4A] border-[#B8D0EC]'
                  : 'bg-white text-[#606973] hover:text-[#142B4A] border-[#E2E6EC]'
              }`}
              title="Toggle advanced linters and LLM gateway options"
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>Options</span>
              {showAdvanced ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>
          </div>

        </div>

        {/* Expandable Advanced Options Drawer */}
        {showAdvanced && (
          <div className="px-4 py-3 bg-[#F8FAFC] border-b border-[#E2E6EC] flex flex-wrap items-center justify-between gap-3 text-xs animate-in fade-in duration-150">
            <div className="flex flex-wrap items-center gap-2.5">
              {/* Static Linters Pill */}
              <div className="flex items-center space-x-1.5 bg-white border border-[#E2E6EC] px-3 py-1.5 rounded-lg font-mono text-[#142B4A]">
                <Terminal className="w-3.5 h-3.5 text-[#142B4A] shrink-0" />
                <span>Linters: {Array.isArray(activeTools) ? activeTools.join(' + ') : activeTools}</span>
              </div>

              {/* LLM Engine Pill */}
              <div
                onClick={onOpenSettings}
                className="flex items-center space-x-2 bg-[#E9E2F5] hover:bg-[#DFD3F0] border border-[#D7C7ED] rounded-lg px-3 py-1.5 cursor-pointer transition-colors"
                title="Configure LLM Gateway & Providers"
              >
                <Cpu className="w-3.5 h-3.5 text-[#4A2E7A] shrink-0" />
                <span className="font-semibold text-[#4A2E7A] uppercase">
                  Engine: {gatewayStatus?.provider || 'OLLAMA'}
                </span>
                <span className="text-[#BFA9D6]">·</span>
                <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-semibold uppercase ${
                  gatewayStatus?.fallback_active
                    ? 'bg-[#FEF3C7] text-[#92400E] border border-[#FDE68A]'
                    : 'bg-white text-[#4A2E7A] border border-[#D7C7ED]'
                }`}>
                  {gatewayStatus?.fallback_state || 'fallback: standby'}
                </span>
              </div>

              {/* Code Metrics Pill */}
              <div className="flex items-center space-x-1.5 font-mono text-[#606973] bg-white border border-[#E2E6EC] px-3 py-1.5 rounded-lg">
                <span>{lineCount} lines</span>
                {fileUploadInfo && (
                  <>
                    <span className="text-[#CBD5E1]">·</span>
                    <span className="text-[#1B5E36] font-bold">{formatBytes(fileUploadInfo.size)}</span>
                  </>
                )}
              </div>

              {/* Auto-Correct on Upload & Drop Toggle */}
              <label 
                className="flex items-center space-x-2 text-xs font-semibold text-[#142B4A] cursor-pointer select-none bg-white border border-[#E2E6EC] hover:border-[#142B4A] px-3 py-1.5 rounded-lg transition-colors shadow-2xs"
                title="Automatically trigger AI analysis and remediation whenever a file is uploaded or dragged & dropped"
              >
                <input
                  type="checkbox"
                  checked={autoCorrectOnUpload}
                  onChange={(e) => setAutoCorrectOnUpload(e.target.checked)}
                  className="w-3.5 h-3.5 text-[#142B4A] rounded border-[#CBD5E1] focus:ring-[#142B4A] cursor-pointer"
                />
                <Sparkles className="w-3.5 h-3.5 text-[#142B4A]" />
                <span>Auto-Correct on Upload / Drop</span>
              </label>
            </div>

            {/* Reset Workspace Action */}
            <button
              onClick={handleResetWorkspace}
              disabled={isAnyExecuting}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-[#606973] hover:text-[#991B1B] hover:bg-[#FEE2E2] border border-transparent hover:border-[#FECACA] transition-colors cursor-pointer disabled:opacity-40"
              title="Reset entire workspace"
            >
              <ResetIcon className="w-3.5 h-3.5" />
              <span>Reset Workspace</span>
            </button>
          </div>
        )}

        {/* Intentionally Vulnerable Benchmark Notice */}
        {samples[language]?.is_intentionally_vulnerable && (
          <div className="px-4 py-2.5 bg-[#FEF3C7] border-b border-[#FDE68A] flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center space-x-2 text-[#92400E]">
              <AlertTriangle className="w-4 h-4 shrink-0 text-[#F59E0B]" />
              <span className="font-semibold text-[#92400E]">
                Benchmark Sample ({language}):
              </span>
              <span className="text-[#78350F]">
                Contains ground-truth vulnerabilities for audit evaluation.
              </span>
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => handleLoadSampleAndAutoCorrect(language)}
                disabled={isAnyExecuting}
                className="bg-[#92400E] hover:bg-[#78350F] text-white px-2.5 py-1 rounded-lg font-semibold flex items-center space-x-1 cursor-pointer transition-colors disabled:opacity-40 shadow-xs"
                title="Auto-correct this benchmark sample immediately"
              >
                <Sparkles className="w-3 h-3 text-[#FDE68A]" />
                <span>Auto-Correct Sample</span>
              </button>
              {onOpenBenchmark && (
                <button
                  onClick={onOpenBenchmark}
                  className="text-xs font-semibold text-[#92400E] hover:text-[#78350F] flex items-center space-x-1 underline cursor-pointer"
                >
                  <span>Benchmark Suite</span>
                  <ArrowUpRight className="w-3.5 h-3.5" />
                </button>
              )}
            </div>
          </div>
        )}

        {/* Editor Window with Gutter and Highlighting */}
        <div 
          ref={editorRef}
          className="flex bg-white relative overflow-hidden" 
          style={{ minHeight: '400px' }}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          {/* Drag & Drop Overlay */}
          {isDraggingOver && (
            <div className="absolute inset-0 z-30 bg-[#142B4A]/95 border-2 border-dashed border-[#DCE7F5] backdrop-blur-xs flex flex-col items-center justify-center pointer-events-none animate-in fade-in">
              <Upload className="w-12 h-12 text-[#DCE7F5] animate-bounce mb-2" />
              <span className="text-base font-bold text-white uppercase tracking-wider">Drop source file to import</span>
              <span className="text-xs text-[#DCE7F5]/80 mt-1 font-mono">
                {autoCorrectOnUpload ? '⚡ Auto-correction enabled on drop' : 'Supports Python, C, C++, Java, JavaScript, Ruby'}
              </span>
            </div>
          )}

          {/* Line Numbers Gutter */}
          <div
            ref={gutterRef}
            className="select-none py-4 px-3 bg-[#F8FAFC] text-[#606973] font-mono text-sm border-r border-[#E2E6EC] text-right overflow-hidden pointer-events-none"
            style={{ minWidth: '3.75rem' }}
          >
            {(code ? code.split('\n') : ['']).map((_, idx) => {
              const lineNum = idx + 1;
              const isTargeted = targetedLine === lineNum;
              return (
                <div
                  key={lineNum}
                  className={`h-7 leading-7 transition-colors ${
                    isTargeted
                      ? 'text-[#142B4A] font-bold bg-[#DCE7F5] px-1 -mx-3 rounded-xs'
                      : 'hover:text-[#142B4A]'
                  }`}
                >
                  {lineNum}
                </div>
              );
            })}
          </div>

          {/* Code Text Area & Syntax Overlay */}
          <div className="flex-1 relative overflow-hidden bg-white">
            {editorMode === 'syntax' && (
              <pre
                ref={preRef}
                aria-hidden="true"
                className="absolute inset-0 m-0 py-4 px-4 font-mono text-sm sm:text-base leading-7 pointer-events-none overflow-hidden select-none whitespace-pre break-normal"
                style={{ lineHeight: '1.75rem', background: 'transparent' }}
              >
                <code 
                  className={`language-${language}`}
                  dangerouslySetInnerHTML={{ __html: highlightedCodeHtml + '\n' }}
                />
              </pre>
            )}

            {/* Interactive Textarea */}
            <textarea
              ref={textareaRef}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              onKeyDown={handleKeyDown}
              onScroll={handleEditorScroll}
              rows={16}
              className={`w-full h-full bg-transparent py-4 px-4 font-mono text-sm sm:text-base focus:outline-none resize-y leading-7 whitespace-pre ${
                editorMode === 'syntax'
                  ? 'text-transparent caret-[#142B4A] selection:bg-[#DCE7F5] selection:text-transparent'
                  : 'text-[#343A40] caret-[#142B4A]'
              }`}
              style={{ lineHeight: '1.75rem' }}
              placeholder="Paste your source code here, upload a file, or select a benchmark sample above..."
              spellCheck={false}
              autoCapitalize="off"
              autoComplete="off"
            />
          </div>
        </div>

      </div>

      {/* =========================================================================
          WORKFLOW STEP 4: PROMINENT CODE CHECK & AUTO-CORRECT ACTIONS
          ========================================================================= */}
      <div className="dev-card p-4 sm:p-5 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 bg-white border border-[#E2E6EC] shadow-sm">
        
        {/* Status Micro-Readout */}
        <div className="flex items-center space-x-3 text-sm">
          <span className={`w-3 h-3 rounded-full shrink-0 ${
            appliedNotice
              ? 'bg-[#10B981]'
              : loadingReview || remediating || rechecking
              ? 'bg-[#142B4A] animate-pulse'
              : reviewState
              ? reviewState.unresolved_count === 0 ? 'bg-[#10B981]' : 'bg-[#F59E0B]'
              : 'bg-[#94A3B8]'
          }`} />
          <div className="flex flex-col">
            <span className="text-[#142B4A] font-bold">
              {appliedNotice
                ? 'Auto-corrected code applied to editor.'
                : loadingReview
                ? 'Running multi-agent review pipeline...'
                : remediating
                ? 'Applying Coder Agent automated fixes...'
                : rechecking
                ? 'Rechecking corrected code against linters...'
                : reviewState
                ? reviewState.unresolved_count === 0
                  ? 'Review complete: Codebase is clean.'
                  : `Review complete: ${reviewState.unresolved_count} actionable finding(s) detected.`
                : 'Ready to review. Press Run Code Review or hit Ctrl+Enter.'}
            </span>
            <span className="text-xs text-[#606973] font-mono mt-0.5">
              {appliedNotice
                ? 'Changes loaded into editor. Run Code Review to verify zero remaining defects.'
                : loadingReview
                ? 'MCP Linters → RAG Retrieval → Security & Bug Agents → Synthesis'
                : reviewState
                ? `Session #${currentSessionIdRef.current} · ${reviewState.issues?.length || 0} total findings analyzed`
                : 'Language: ' + language.toUpperCase() + ' · Tools: ' + (Array.isArray(activeTools) ? activeTools.join(', ') : activeTools)}
            </span>
          </div>
        </div>

        {/* Primary Action Button Deck with Auto-Correct Options */}
        <div className="flex flex-wrap items-center gap-2.5 sm:gap-3 shrink-0">
          
          {/* Auto-Correct on Review Checkbox Option */}
          <label 
            className={`flex items-center space-x-2 text-xs font-semibold px-3 py-2 rounded-xl border transition-all cursor-pointer select-none ${
              autoCorrectOnReview 
                ? 'bg-[#EBF3FC] text-[#142B4A] border-[#B8D0EC] shadow-2xs font-bold' 
                : 'bg-[#F8FAFC] text-[#606973] border-[#E2E6EC] hover:text-[#142B4A]'
            }`}
            title="Automatically run Coder Agent auto-remediation when actionable defects are detected"
          >
            <input
              type="checkbox"
              checked={autoCorrectOnReview}
              onChange={(e) => setAutoCorrectOnReview(e.target.checked)}
              className="w-3.5 h-3.5 rounded text-[#142B4A] cursor-pointer"
            />
            <span>Auto-Correct on Review</span>
          </label>

          {/* Cancel button if running */}
          {isAnyExecuting && (
            <button
              onClick={handleCancelExecution}
              className="flex items-center space-x-2 px-3.5 py-2.5 rounded-xl text-xs font-bold uppercase tracking-wider text-[#991B1B] bg-[#FEE2E2] hover:bg-[#FED7D7] border border-[#FECACA] transition-all cursor-pointer shadow-sm"
              title="Safely cancel ongoing analysis"
            >
              <StopCircle className="w-4 h-4 text-[#EF4444]" />
              <span>Cancel</span>
            </button>
          )}

          {/* Code Check: Run Review Button */}
          <button
            onClick={() => handleRunReview()}
            disabled={isAnyExecuting || !code.trim()}
            title={autoCorrectOnReview ? "Run Code Review & Auto-Correct (Ctrl+Enter)" : "Run Code Review (Ctrl+Enter)"}
            className="dev-btn-primary h-12 px-6 sm:px-7 text-xs sm:text-sm font-bold tracking-wider uppercase cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shadow-md flex items-center space-x-2"
          >
            {loadingReview ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Analyzing Code...</span>
              </>
            ) : autoCorrectOnReview ? (
              <>
                <Sparkles className="w-4 h-4 text-white" />
                <span>Review &amp; Auto-Fix</span>
                <span className="text-[10px] font-mono opacity-80 ml-1 hidden md:inline">Ctrl+↵</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-white" />
                <span>Run Code Review</span>
                <span className="text-[10px] font-mono opacity-80 ml-1 hidden md:inline">Ctrl+↵</span>
              </>
            )}
          </button>

          {/* Dedicated Auto-Correct Button from Code Check */}
          <button
            onClick={handleAutoCorrectClick}
            disabled={isAnyExecuting || !code.trim() || (reviewState && reviewState.unresolved_count === 0)}
            title={
              reviewState && reviewState.unresolved_count === 0
                ? "Code is clean — zero actionable defects"
                : "Auto-correct detected defects using Coder Agent (Shift+Ctrl+Enter)"
            }
            className={`h-12 px-5 text-xs sm:text-sm font-bold uppercase tracking-wider rounded-xl transition-all cursor-pointer flex items-center space-x-2 shadow-sm ${
              reviewState && reviewState.unresolved_count === 0
                ? 'bg-[#EAEFEA] text-[#1B5E36] border border-[#BDE0D7] opacity-60 cursor-not-allowed'
                : 'bg-white hover:bg-[#F0F5FA] text-[#142B4A] border-2 border-[#142B4A]'
            } disabled:opacity-40 disabled:cursor-not-allowed`}
          >
            {remediating ? (
              <>
                <span className="w-4 h-4 border-2 border-[#142B4A] border-t-transparent rounded-full animate-spin" />
                <span>Auto-Correcting...</span>
              </>
            ) : reviewState && reviewState.unresolved_count === 0 ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-[#10B981]" />
                <span>All Clean</span>
              </>
            ) : (
              <>
                <Wrench className="w-4 h-4 text-[#142B4A]" />
                <span>
                  {reviewState && reviewState.unresolved_count > 0
                    ? `Auto-Correct (${reviewState.unresolved_count})`
                    : 'Auto-Correct'}
                </span>
              </>
            )}
          </button>

          {/* "after the change of auto correct" -> Apply Fix to Editor */}
          {hasAutoCorrectChanges && (
            <button
              onClick={() => handleApplyToEditor()}
              disabled={isAnyExecuting}
              className="h-12 px-5 text-xs sm:text-sm font-bold uppercase tracking-wider cursor-pointer bg-[#10B981] hover:bg-[#059669] text-white rounded-xl shadow-md flex items-center space-x-2 transition-all animate-in fade-in disabled:opacity-40"
              title="Apply the auto-corrected code directly into your editor above"
            >
              <CheckCircle2 className="w-4 h-4 text-white" />
              <span>Apply Fix to Editor</span>
            </button>
          )}

          {/* Revert Button if code was applied */}
          {previousCodeBeforeApply !== null && (
            <button
              onClick={handleRevertAppliedCode}
              disabled={isAnyExecuting}
              className="dev-btn-secondary h-12 px-3 text-xs font-semibold cursor-pointer text-[#606973] hover:text-[#991B1B] flex items-center space-x-1.5"
              title="Revert editor to code prior to applying auto-correction"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Revert</span>
            </button>
          )}

        </div>

      </div>

      {/* Applied Notice Banner ("after the change of auto correct") */}
      {appliedNotice && (
        <div className="p-3.5 sm:p-4 rounded-xl bg-[#DCFCE7] border border-[#BBF7D0] flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-[#166534] text-xs sm:text-sm shadow-sm animate-in fade-in">
          <div className="flex items-center space-x-2.5">
            <CheckCircle2 className="w-5 h-5 text-[#16A34A] shrink-0" />
            <span className="font-semibold">
              Auto-corrected code applied to editor! Active Health Score updated to{' '}
              <span className="font-mono font-black text-sm bg-white px-2 py-0.5 rounded border border-[#BBF7D0] text-[#15803D]">
                {(reviewState?.post_fix_score ?? reviewState?.health_score ?? 10.0).toFixed(1)} / 10.0
              </span>.
            </span>
          </div>
          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={() => handleRunReview(false)}
              disabled={isAnyExecuting}
              className="px-3.5 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider bg-[#16A34A] hover:bg-[#15803D] text-white transition-colors cursor-pointer shadow-2xs"
            >
              Verify Clean Status
            </button>
            <button
              onClick={handleRevertAppliedCode}
              className="px-2.5 py-1.5 rounded-lg text-xs font-medium text-[#166534] hover:bg-[#BBF7D0] transition-colors cursor-pointer"
            >
              Undo
            </button>
          </div>
        </div>
      )}

      {/* =========================================================================
          WORKFLOW STEP 5: VISIBLE COMPACT PIPELINE WITH REAL EXECUTION STATUSES
          ========================================================================= */}
      <PipelineTelemetry
        telemetry={reviewState?.telemetry || []}
        isLoading={loadingReview || remediating || rechecking}
        isRemediating={remediating}
        isRechecking={rechecking}
        issuesCount={reviewState?.issues?.length || 0}
        totalElapsedMs={reviewState?.total_elapsed_ms}
        reviewState={reviewState}
      />

      {/* =========================================================================
          WORKFLOW STEP 6: REVIEW SUMMARY WITH HEALTH SCORE, VERDICT & SUMMARY
          ========================================================================= */}
      <TriageVerdict
        healthScore={reviewState?.health_score ?? 10.0}
        postFixScore={reviewState?.post_fix_score}
        preFixScore={reviewState?.pre_fix_score ?? reviewState?.initial_health_score}
        appliedToEditor={Boolean(reviewState?.applied_to_editor)}
        verdict={reviewState?.verdict || 'PENDING'}
        summary={reviewState?.summary || 'Run the review pipeline to execute static analysis, RAG grounding, and multi-agent triage.'}
        counts={reviewState?.counts || { critical: 0, high: 0, medium: 0, low: 0 }}
        unresolvedCount={reviewState?.unresolved_count ?? 0}
        resolvedCount={reviewState?.resolved_count ?? 0}
        remediationStatus={reviewState?.remediation_status || 'NOT_REQUIRED'}
        autoFixFailure={reviewState?.auto_fix_failure || false}
        hasRun={Boolean(reviewState)}
      />

      <ReviewHeader
        filename={reviewState?.filename || filename}
        language={reviewState?.language || language}
        reviewId={reviewState?.review_id}
        verdict={reviewState?.verdict || (loadingReview ? 'ANALYZING...' : 'PENDING')}
        remediationStatus={reviewState?.remediation_status || 'NOT_REQUIRED'}
        mcpTools={reviewState?.mcp_tools || activeTools}
        gatewayStatus={gatewayStatus}
        executionStatus={
          loadingReview ? 'Running Review Pipeline...' :
          remediating ? 'Applying Coder Remediation...' :
          rechecking ? 'Executing Re-Check...' :
          reviewState ? 'Completed' : 'Ready'
        }
        executionTime={reviewState?.telemetry?.[0]?.latency_ms ? `${reviewState.telemetry[0].latency_ms}ms` : null}
      />

      {/* =========================================================================
          WORKFLOW STEP 7: FINDINGS GROUPED BY SECURITY, BUGS & CODE QUALITY
          ========================================================================= */}
      <IssueList
        issues={reviewState?.issues || []}
        filename={reviewState?.filename || filename}
        onSelectLine={handleSelectLine}
        onToggleIgnore={handleToggleIgnore}
      />

      {/* =========================================================================
          WORKFLOW STEP 8: ORIGINAL-VERSUS-CORRECTED CODE DIFF
          ========================================================================= */}
      <CodeDiffViewer
        originalCode={reviewState?.original_code || code}
        correctedCode={reviewState?.corrected_code || code}
        changelog={reviewState?.changelog || []}
        language={language}
        filename={filename}
        reviewId={reviewState?.review_id}
        unresolvedCount={reviewState?.unresolved_count ?? 0}
        resolvedCount={reviewState?.resolved_count ?? 0}
        remediationStatus={reviewState?.remediation_status || 'NOT_REQUIRED'}
        autoFixFailure={reviewState?.auto_fix_failure || false}
        mcpTools={reviewState?.mcp_tools || activeTools}
        targetedLine={targetedLine}
        onApplyFix={handleApplyFix}
        onRecheck={handleManualRecheck}
        onApplyToEditor={handleApplyToEditor}
        remediating={remediating}
        rechecking={rechecking}
        fixStateMessage={fixStateMessage}
        postFixScore={reviewState?.post_fix_score ?? (reviewState?.remediation_status === 'SUCCESS' ? reviewState?.health_score : null)}
      />

      {/* =========================================================================
          WORKFLOW STEP 9: REPORT & DOWNLOAD ACTIONS
          ========================================================================= */}
      <AuditReportSection
        reviewResult={reviewState}
        gatewayStatus={gatewayStatus}
      />

    </div>
  );
}

