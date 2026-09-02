import React, { useState, useRef, useEffect } from 'react';
import { 
  Bot, 
  Send, 
  User, 
  Sparkles, 
  RefreshCw, 
  HelpCircle,
  Zap,
  Trash2,
  Copy,
  Check,
  Image as ImageIcon,
  X,
  Package,
  ArrowRight
} from 'lucide-react';
import { scanApi, llmApi } from '../services/api';
import type { AnalyzeScanResponse } from '../types/api';

// ── Groq Config ──────────────────────────────────────────────
const GROQ_API_KEY = import.meta.env.VITE_GROQ_API_KEY || '';
const GROQ_API_URL = 'https://api.groq.com/openai/v1/chat/completions';
const GROQ_MODELS = ['openai/gpt-oss-20b', 'qwen/qwen3.6-27b', 'allam-2-7b'];

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  imageSrc?: string;
  isError?: boolean;
  scanData?: AnalyzeScanResponse;
}

interface ChatAssistantProps {
  scanResult?: AnalyzeScanResponse | null;
  originalImageSrc?: string;
  onOpenScanTab?: () => void;
  onClose?: () => void;
}

// ── Markdown Block & Inline Renderer ─────────────────────────
const renderMarkdown = (text: string) => {
  if (!text) return '';

  // Preserve preformatted code blocks
  const codeBlockMap: string[] = [];
  let processedText = text.replace(/```([\s\S]*?)```/g, (_match, code) => {
    const placeholder = `___CODE_BLOCK_${codeBlockMap.length}___`;
    codeBlockMap.push(
      `<pre class="my-2.5 p-3.5 rounded-xl bg-slate-950 border border-white/10 font-mono text-xs text-sky-300 overflow-x-auto text-left leading-normal">${code.trim()}</pre>`
    );
    return placeholder;
  });

  const lines = processedText.split('\n');
  const htmlChunks: string[] = [];
  let inTable = false;

  for (let i = 0; i < lines.length; i++) {
    let line = lines[i].trim();

    if (!line) {
      if (inTable) {
        htmlChunks.push('</tbody></table></div>');
        inTable = false;
      }
      continue;
    }

    // Markdown Table Row
    if (line.startsWith('|') && line.endsWith('|')) {
      if (line.includes('---')) continue; // Skip separator line
      const cells = line.split('|').map(c => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
      if (!inTable) {
        inTable = true;
        htmlChunks.push('<div class="my-2.5 overflow-x-auto rounded-xl border border-white/10 bg-black/40"><table class="w-full text-left text-xs border-collapse">');
        htmlChunks.push('<thead class="bg-white/5 border-b border-white/10"><tr>');
        cells.forEach(c => htmlChunks.push(`<th class="px-3 py-2 font-bold text-slate-200 border-r border-white/5 last:border-r-0">${c}</th>`));
        htmlChunks.push('</tr></thead><tbody>');
      } else {
        htmlChunks.push('<tr class="border-b border-white/5 hover:bg-white/2">');
        cells.forEach(c => htmlChunks.push(`<td class="px-3 py-2 text-slate-300 border-r border-white/5 last:border-r-0">${c}</td>`));
        htmlChunks.push('</tr>');
      }
      continue;
    } else if (inTable) {
      htmlChunks.push('</tbody></table></div>');
      inTable = false;
    }

    // Headings
    if (line.startsWith('### ')) {
      htmlChunks.push(`<h4 class="font-bold text-slate-100 text-xs sm:text-sm mt-3 mb-1 text-left border-b border-white/5 pb-1">${line.slice(4)}</h4>`);
      continue;
    }
    if (line.startsWith('## ')) {
      htmlChunks.push(`<h3 class="font-extrabold text-white text-sm sm:text-base mt-3.5 mb-1.5 text-left font-display border-b border-white/10 pb-1">${line.slice(3)}</h3>`);
      continue;
    }
    if (line.startsWith('# ')) {
      htmlChunks.push(`<h2 class="font-extrabold text-white text-base sm:text-lg mt-4 mb-2 text-left font-display">${line.slice(2)}</h2>`);
      continue;
    }

    // Bullet lists (- , * , • )
    if (/^[-*•]\s+/.test(line)) {
      const content = line.replace(/^[-*•]\s+/, '');
      htmlChunks.push(`<div class="flex items-start gap-2.5 text-left my-1 pl-1"><span class="w-1.5 h-1.5 rounded-full bg-sky-400 mt-1.5 flex-shrink-0"></span><span class="text-slate-200 text-xs sm:text-sm leading-relaxed">${content}</span></div>`);
      continue;
    }

    // Numbered lists (1. , 2. )
    if (/^\d+\.\s+/.test(line)) {
      const match = line.match(/^(\d+)\.\s+(.*)/);
      if (match) {
        htmlChunks.push(`<div class="flex items-start gap-2 text-left my-1 pl-1"><span class="font-mono font-bold text-sky-400 text-xs flex-shrink-0 mt-0.5">${match[1]}.</span><span class="text-slate-200 text-xs sm:text-sm leading-relaxed">${match[2]}</span></div>`);
        continue;
      }
    }

    // Blockquotes
    if (line.startsWith('> ')) {
      htmlChunks.push(`<blockquote class="pl-3 border-l-2 border-sky-400 text-slate-400 italic text-xs my-2 text-left bg-sky-500/5 py-1.5 rounded-r-lg">${line.slice(2)}</blockquote>`);
      continue;
    }

    // Normal paragraph line
    htmlChunks.push(`<p class="text-left my-1 text-xs sm:text-sm text-slate-200 leading-relaxed">${line}</p>`);
  }

  if (inTable) {
    htmlChunks.push('</tbody></table></div>');
  }

  let finalHtml = htmlChunks.join('');

  // Restore code blocks
  codeBlockMap.forEach((blockHtml, idx) => {
    finalHtml = finalHtml.replace(`___CODE_BLOCK_${idx}___`, blockHtml);
  });

  // Inline formatting
  finalHtml = finalHtml.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-white">$1</strong>');
  finalHtml = finalHtml.replace(/\*(.*?)\*/g, '<em class="italic text-slate-300">$1</em>');
  finalHtml = finalHtml.replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-black/40 border border-white/10 font-mono text-sky-300 text-[11px]">$1</code>');

  return finalHtml;
};

export const ChatAssistant: React.FC<ChatAssistantProps> = ({
  scanResult,
  originalImageSrc,
  onOpenScanTab,
  onClose,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputPrompt, setInputPrompt] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeScan, setActiveScan] = useState<AnalyzeScanResponse | null>(scanResult || null);
  const [activeImage, setActiveImage] = useState<string | null>(originalImageSrc || null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Sync active scan from props if updated
  useEffect(() => {
    if (scanResult) {
      setActiveScan(scanResult);
      if (originalImageSrc) setActiveImage(originalImageSrc);
    }
  }, [scanResult, originalImageSrc]);

  // Initial welcome message
  useEffect(() => {
    const welcomeContent = scanResult
      ? `Hello! I have loaded your package scan context for **"${scanResult.compliance_result.product_name || 'Pre-Packaged Commodity'}"** (Score: ${scanResult.compliance_result.compliance_score.toFixed(0)}%, Status: ${scanResult.compliance_result.overall_status}).\n\nAsk me anything about this scan, its extracted declarations, or rule violations!`
      : "Hello! I am **LegalMetrix AI**, powered by Groq. You can ask general compliance questions or **upload a package image** below to analyze its labelling and compliance instantly!";

    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content: welcomeContent,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ]);
  }, [scanResult]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Image Selection Handler
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setImagePreview(url);
    }
  };

  const handleClearImage = () => {
    setSelectedFile(null);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  // ── LLM Explain via Backend ─────────────────────────────
  const callLLMExplain = async (scanContext: AnalyzeScanResponse): Promise<string | null> => {
    const rawOcrText = (scanContext as any).ocr_summary?.raw_text || '';
    if (!rawOcrText || !GROQ_API_KEY) return null;
    try {
      const found = scanContext.extraction_insight?.found_features || [];
      const extractedFields: Record<string, string> = {};
      found.forEach(f => { if (f.value) extractedFields[f.label] = f.value; });
      const currentDate = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
      const result = await llmApi.explainLabel({
        raw_ocr_text: rawOcrText,
        groq_api_key: GROQ_API_KEY,
        current_date: currentDate,
        extracted_fields: extractedFields,
      });
      return result.explanation;
    } catch (err) {
      console.warn('Backend LLM explain failed, falling back to Groq direct', err);
      return null;
    }
  };

  // ── Construct Context Prompt ──────────────────────────────
  const buildSystemPrompt = (scanContext?: AnalyzeScanResponse | null) => {
    const currentDateStr = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
    let prompt = `You are LegalMetrix AI, an intelligent package label analysis assistant.

When a package image or scan context is provided:
1. Carefully analyze the ACTUAL label image details and the raw OCR text. The raw OCR text is the ground truth — always prefer it over pre-extracted fields which may have OCR errors.
2. Dynamically categorize and present ONLY the details actually found on the label (e.g. Barcode, Batch/Coding, Price & Net Weight, Storage Instructions, Manufacturer/Marketer, Contact details). Do NOT invent missing fields.
3. Silently correct obvious OCR artifacts (e.g. year 2826 → 2026, "0.1 m" when label says "1 Liter" → 1 L / 100 g, Indian cities like Madurai → Country of Origin: India).
4. If dates are present, calculate a "Quick status (as of ${currentDateStr})" stating whether the product is within its usable period.
5. Format your output using clean, left-aligned markdown headings and bullet points.
6. End with a polite follow-up offering further assistance.`;

    if (scanContext) {
      const c = scanContext.compliance_result;
      const found = scanContext.extraction_insight?.found_features || [];
      const missing = scanContext.extraction_insight?.missing_fields || [];
      const failed = c.results.filter(r => r.status === 'FAIL');
      // Use raw_text from ocr_summary (now populated by backend)
      const rawOcrText = (scanContext as any).ocr_summary?.raw_text || '';

      prompt += `\n\nFULL RAW OCR TEXT FROM LABEL IMAGE (ground truth — use this to correct field errors):
"""
${rawOcrText || '(No raw OCR text available)'}
"""

- Product Name: ${c.product_name || 'Pre-Packaged Commodity'}
- Overall Compliance Status: ${c.overall_status} (${c.compliance_score.toFixed(0)}%)
- Pre-Extracted Declarations (${found.length}) [may contain OCR errors — validate against raw OCR text above]:
${found.map(f => `  * ${f.label}: "${f.value}"`).join('\n') || '  (None)'}
- Missing Required Declarations (${missing.length}): ${missing.map(m => m.label).join(', ') || 'None'}
- Compliance Issues / Violations (${failed.length}):
${failed.map(r => `  * ${r.rule_name}: ${r.reason}`).join('\n') || '  None'}

Carefully analyze ALL raw OCR text lines, text snippets, and structured declarations above to answer the user!`;
    }

    return prompt;
  };


  // ── Send Handler ──────────────────────────────────────────
  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputPrompt).trim();
    if (!query && !selectedFile) return;
    if (isLoading) return;

    let uploadedScan: AnalyzeScanResponse | undefined = undefined;
    let currentImagePreview = imagePreview;
    let fileToUpload = selectedFile;

    // Clear inputs immediately
    setInputPrompt('');
    setSelectedFile(null);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    setIsLoading(true);

    // If an image was attached directly in chat, run OCR scan first
    if (fileToUpload) {
      try {
        uploadedScan = await scanApi.analyzeImage(fileToUpload, { persist: true });
        setActiveScan(uploadedScan);
        if (currentImagePreview) setActiveImage(currentImagePreview);
      } catch (err: any) {
        console.warn('Image OCR failed, proceeding with LLM context', err);
      }
    }

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: query || (fileToUpload ? 'Analyzed uploaded image' : ''),
      imageSrc: currentImagePreview || undefined,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMsg]);

    const currentScanContext = uploadedScan || activeScan;

    // ── Route image-analysis/explain requests to backend LLM endpoint ──
    // Matches: new image upload, or explain/analyze/describe/summarize/extract text queries
    const isExplainQuery = !query ||
      /explain|analyze|describe|summarize|extract|what.*label|what.*image|tell me|read.*label|show.*details|what.*product/i.test(query);

    if (currentScanContext && isExplainQuery && GROQ_API_KEY) {
      const llmReply = await callLLMExplain(currentScanContext);
      if (llmReply) {
        const assistantMsg: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: llmReply,
          scanData: uploadedScan,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, assistantMsg]);
        setIsLoading(false);
        inputRef.current?.focus();
        return;
      }
    }

    // ── Fall back to direct Groq with system prompt context ──
    const systemPrompt = buildSystemPrompt(currentScanContext);

    // Build chat history
    const history = messages
      .filter(m => m.id !== 'welcome')
      .slice(-8)
      .map(m => ({ role: m.role, content: m.content }));

    let promptContent = query;
    if (uploadedScan && !query) {
      promptContent = `Please analyze the uploaded image label details and present the extracted fields, usability status, and compliance summary based on what is actually present on the label.`;
    } else if (uploadedScan && query) {
      promptContent = `[Image uploaded]. ${query}`;
    }

    history.push({ role: 'user', content: promptContent });

    try {
      let reply = '';
      let success = false;
      let lastError = '';

      for (const model of GROQ_MODELS) {
        try {
          const res = await fetch(GROQ_API_URL, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${GROQ_API_KEY}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              model,
              messages: [
                { role: 'system', content: systemPrompt },
                ...history,
              ],
              temperature: 0.5,
              max_tokens: 1024,
              stream: false,
            }),
          });

          if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            lastError = errData?.error?.message || `Groq API error: ${res.status}`;
            continue;
          }

          const data = await res.json();
          reply = data.choices?.[0]?.message?.content ?? 'No response received.';
          success = true;
          break;
        } catch (err: any) {
          lastError = err?.message || 'Network error';
        }
      }

      if (success) {
        const assistantMsg: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: reply,
          scanData: uploadedScan,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } else {
        const errorMsg: ChatMessage = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `⚠️ ${lastError || 'Could not reach the AI. Please check your connection and try again.'}`,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          isError: true,
        };
        setMessages((prev) => [...prev, errorMsg]);
      }
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleClear = () => {
    setMessages([{
      id: 'welcome-new',
      role: 'assistant',
      content: "Conversation cleared. How can I help you?",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }]);
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    });
  };

  // Dynamic suggested prompts
  const suggestedPrompts = activeScan ? [
    '📄 Extract and summarize all text from this image',
    `Why did "${activeScan.compliance_result.product_name || 'this package'}" get a ${activeScan.compliance_result.compliance_score.toFixed(0)}% score?`,
    'Summarize all extracted declarations from this package',
    'How can the manufacturer fix the compliance issues?',
  ] : [
    'What details must be on a product label?',
    'What is the MRP format requirement?',
    'How is net quantity checked for liquids?',
    'What font size is required for labels?',
  ];


  return (
    <div className="w-full max-w-4xl mx-auto flex flex-col h-[calc(100vh-148px)] min-h-[560px] rounded-2xl border border-white/5 overflow-hidden animate-fade-in"
      style={{ background: 'rgba(8,15,30,0.85)', backdropFilter: 'blur(24px)' }}
    >
      {/* ── Header ── */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-white/5"
        style={{ background: 'rgba(13,22,40,0.9)' }}
      >
        <div className="flex items-center gap-3">
          <div className="relative w-9 h-9 rounded-xl flex items-center justify-center text-white shadow-lg"
            style={{ background: 'linear-gradient(135deg, #0171c7, #4f46e5)' }}
          >
            <Bot className="w-5 h-5" />
            <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-[#0d1628]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-white font-display">LegalMetrix AI</h2>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold border"
                style={{ background: 'rgba(14,165,233,0.08)', borderColor: 'rgba(14,165,233,0.2)', color: '#7dd3fc' }}
              >
                <Zap className="w-2.5 h-2.5" /> Groq · Image & Text AI
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-0.5">Package & Labelling Compliance Assistant</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {activeScan && onOpenScanTab && (
            <button onClick={onOpenScanTab}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-sky-500/10 hover:bg-sky-500/20 text-sky-300 border border-sky-500/20 text-xs font-semibold transition-all">
              <span>View Full Report</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
          <button onClick={handleClear} title="Clear conversation"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-white/5 border border-transparent hover:border-white/5 transition-all text-xs font-medium">
            <Trash2 className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Clear</span>
          </button>
          {(onClose || onOpenScanTab) && (
            <button
              onClick={onClose || onOpenScanTab}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/20 text-xs font-bold transition-all active:scale-95 ml-1"
              title="Exit Chatbot"
            >
              <X className="w-4 h-4 text-rose-400" />
              <span>Exit</span>
            </button>
          )}
        </div>
      </div>

      {/* ── Active Scan Context Banner ── */}
      {activeScan && (
        <div className="px-5 py-3 border-b border-sky-500/20 bg-sky-950/20 flex items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-3 min-w-0">
            {activeImage ? (
              <div className="w-10 h-10 rounded-lg overflow-hidden border border-white/10 flex-shrink-0 bg-black">
                <img src={activeImage} alt="Scanned Package" className="w-full h-full object-cover" />
              </div>
            ) : (
              <div className="w-9 h-9 rounded-lg bg-sky-500/15 border border-sky-500/30 flex items-center justify-center flex-shrink-0">
                <Package className="w-4 h-4 text-sky-400" />
              </div>
            )}
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-bold text-white truncate">
                  {activeScan.compliance_result.product_name || 'Active Package Scan'}
                </span>
                <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold ${
                  activeScan.compliance_result.overall_status === 'COMPLIANT'
                    ? 'badge-pass'
                    : activeScan.compliance_result.overall_status === 'POTENTIALLY_NON_COMPLIANT'
                    ? 'badge-warn'
                    : 'badge-fail'
                }`}>
                  {activeScan.compliance_result.overall_status.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 mt-0.5 truncate">
                Score: <strong className="text-sky-300">{activeScan.compliance_result.compliance_score.toFixed(0)}%</strong>
                {' '}· {activeScan.extraction_insight?.found_features?.length || 0} fields extracted
              </p>
            </div>
          </div>
          <button onClick={() => { setActiveScan(null); setActiveImage(null); }}
            className="text-[10px] text-slate-500 hover:text-slate-300 px-2 py-1 rounded bg-white/5 border border-white/5 transition-colors flex-shrink-0">
            Clear Context
          </button>
        </div>
      )}

      {/* ── Messages ── */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-5 space-y-5">
        {messages.map((msg) => (
          <div key={msg.id}
            className={`flex items-start gap-3 animate-fade-in ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
          >
            {/* Avatar */}
            <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-xs font-bold ${
              msg.role === 'user'
                ? 'text-white'
                : msg.isError
                ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                : 'bg-indigo-500/15 text-indigo-300 border border-indigo-500/30'
            }`}
              style={msg.role === 'user' ? { background: 'linear-gradient(135deg, #0171c7, #4f46e5)' } : {}}
            >
              {msg.role === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            {/* Bubble */}
            <div className={`group relative max-w-[85%] sm:max-w-[78%] ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col gap-1.5`}>
              
              {/* Image Preview in Message */}
              {msg.imageSrc && (
                <div className="w-48 h-36 rounded-xl overflow-hidden border border-white/10 bg-black shadow-lg">
                  <img src={msg.imageSrc} alt="Attached Package" className="w-full h-full object-cover" />
                </div>
              )}

              {/* Text Bubble */}
              {msg.content && (
                <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === 'user'
                    ? 'text-white rounded-tr-sm'
                    : msg.isError
                    ? 'bg-rose-950/20 border border-rose-500/20 text-rose-300 rounded-tl-sm'
                    : 'text-slate-200 rounded-tl-sm border border-white/5'
                }`}
                  style={
                    msg.role === 'user'
                      ? { background: 'linear-gradient(135deg, #0171c7, #4f46e5)' }
                      : msg.isError ? {} : { background: 'rgba(17,31,56,0.9)' }
                  }
                >
                  <div
                    className="text-left w-full overflow-hidden text-slate-200"
                    dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
                  />
                </div>
              )}

              {/* Uploaded Scan Summary Card if present */}
              {msg.scanData && (
                <div className="w-full p-3.5 rounded-xl border border-sky-500/25 bg-sky-950/30 space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-sky-400" />
                      OCR Inspection Analysis
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                      msg.scanData.compliance_result.overall_status === 'COMPLIANT' ? 'badge-pass' : 'badge-fail'
                    }`}>
                      {msg.scanData.compliance_result.overall_status.replace(/_/g, ' ')}
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div className="p-2 rounded bg-black/40 border border-white/5">
                      <span className="text-slate-500 block">Score</span>
                      <strong className="text-sky-300 text-sm font-mono">
                        {msg.scanData.compliance_result.compliance_score.toFixed(0)}%
                      </strong>
                    </div>
                    <div className="p-2 rounded bg-black/40 border border-white/5">
                      <span className="text-slate-500 block">Extracted Fields</span>
                      <strong className="text-emerald-300 text-sm font-mono">
                        {msg.scanData.extraction_insight?.found_features?.length || 0}
                      </strong>
                    </div>
                  </div>
                </div>
              )}

              {/* Timestamp + Copy */}
              <div className={`flex items-center gap-2 px-1 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <span className="text-[10px] text-slate-600">{msg.timestamp}</span>
                {msg.role === 'assistant' && !msg.isError && (
                  <button
                    onClick={() => handleCopy(msg.id, msg.content)}
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-slate-600 hover:text-slate-300"
                    title="Copy message"
                  >
                    {copiedId === msg.id
                      ? <Check className="w-3 h-3 text-emerald-400" />
                      : <Copy className="w-3 h-3" />
                    }
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {isLoading && (
          <div className="flex items-start gap-3 animate-fade-in">
            <div className="w-8 h-8 rounded-xl bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4" />
            </div>
            <div className="px-4 py-3 rounded-2xl rounded-tl-sm border border-white/5 flex items-center gap-3"
              style={{ background: 'rgba(17,31,56,0.9)' }}
            >
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-sky-400 flex-shrink-0" />
              <div className="flex items-center gap-1">
                {[0, 1, 2].map(i => (
                  <span key={i} className="w-1.5 h-1.5 rounded-full bg-sky-400/60 animate-pulse"
                    style={{ animationDelay: `${i * 200}ms` }} />
                ))}
              </div>
              <span className="text-xs text-slate-400">
                {selectedFile ? 'Analyzing image & inspecting compliance...' : 'Thinking...'}
              </span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── Image Attachment Bar (when file is selected) ── */}
      {imagePreview && (
        <div className="px-4 py-2 border-t border-sky-500/20 bg-sky-950/30 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg overflow-hidden border border-sky-400/40 bg-black flex-shrink-0">
              <img src={imagePreview} alt="Preview" className="w-full h-full object-cover" />
            </div>
            <div>
              <span className="text-xs font-bold text-white block truncate max-w-xs">{selectedFile?.name}</span>
              <span className="text-[10px] text-sky-400">Ready to analyze with AI</span>
            </div>
          </div>
          <button onClick={handleClearImage}
            className="p-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 text-xs border border-rose-500/20 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* ── Suggested Prompts ── */}
      <div className="px-4 py-2 border-t border-white/4 flex items-center gap-2 overflow-x-auto"
        style={{ background: 'rgba(8,15,30,0.7)' }}
      >
        <HelpCircle className="w-3 h-3 text-slate-600 flex-shrink-0" />
        <div className="flex items-center gap-2 overflow-x-auto pb-0.5">
          {suggestedPrompts.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleSendMessage(prompt)}
              disabled={isLoading}
              className="flex-shrink-0 px-3 py-1.5 rounded-full text-[11px] font-medium text-slate-400 hover:text-sky-300 border border-white/5 hover:border-sky-500/30 transition-all hover:bg-sky-500/5 disabled:opacity-40 whitespace-nowrap"
              style={{ background: 'rgba(255,255,255,0.03)' }}
            >
              {prompt}
            </button>
          ))}
        </div>
      </div>

      {/* ── Input Box ── */}
      <div className="px-4 py-3 border-t border-white/5 flex items-center gap-2.5"
        style={{ background: 'rgba(13,22,40,0.95)' }}
      >
        {/* Hidden File Input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleFileChange}
          className="hidden"
        />

        {/* Image Attachment Button */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          title="Upload image to ask AI"
          className={`w-11 h-11 rounded-xl flex items-center justify-center border transition-all flex-shrink-0 ${
            imagePreview
              ? 'bg-sky-500/20 border-sky-400 text-sky-300 shadow-glow'
              : 'bg-white/4 hover:bg-white/8 border-white/8 text-slate-400 hover:text-slate-200'
          }`}
        >
          <ImageIcon className="w-5 h-5" />
        </button>

        {/* Text Input */}
        <div className="flex-1 relative">
          <input
            ref={inputRef}
            type="text"
            value={inputPrompt}
            onChange={(e) => setInputPrompt(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) handleSendMessage(); }}
            placeholder={
              selectedFile
                ? "Type a question about this image (or press send for full analysis)..."
                : activeScan
                ? `Ask anything about "${activeScan.compliance_result.product_name || 'this package'}"...`
                : "Ask a compliance question or upload a package image..."
            }
            className="w-full rounded-xl px-4 py-3 text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-sky-500/40 transition-all pr-10"
            style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
            disabled={isLoading}
          />
          {inputPrompt && (
            <button onClick={() => setInputPrompt('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-400 transition-colors text-xs">
              ✕
            </button>
          )}
        </div>

        {/* Send Button */}
        <button
          onClick={() => handleSendMessage()}
          disabled={(!inputPrompt.trim() && !selectedFile) || isLoading}
          className="w-11 h-11 rounded-xl flex items-center justify-center text-white transition-all active:scale-95 disabled:opacity-30 flex-shrink-0 shadow-lg"
          style={{
            background: 'linear-gradient(135deg, #0171c7, #4f46e5)',
            boxShadow: (inputPrompt.trim() || selectedFile) ? '0 4px 15px rgba(14,165,233,0.35)' : 'none'
          }}
          title="Send (Enter)"
        >
          {isLoading
            ? <RefreshCw className="w-4 h-4 animate-spin" />
            : <Send className="w-4 h-4" />
          }
        </button>
      </div>

      {/* Powered by strip */}
      <div className="px-5 py-1.5 text-center border-t border-white/4"
        style={{ background: 'rgba(8,15,30,0.9)' }}
      >
        <p className="text-[10px] text-slate-700 flex items-center justify-center gap-1.5">
          <Sparkles className="w-2.5 h-2.5" />
          Powered by Groq Cloud · Image OCR & Multi-Model Inference
        </p>
      </div>
    </div>
  );
};
