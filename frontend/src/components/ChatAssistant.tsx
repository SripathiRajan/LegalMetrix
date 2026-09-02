import React, { useState, useRef, useEffect } from 'react';
import { 
  Bot, 
  Send, 
  User, 
  FileText, 
  BookOpen, 
  Sparkles, 
  RefreshCw, 
  HelpCircle,
  Database
} from 'lucide-react';
import { chatApi } from '../services/api';
import type { ChatResponse, Citation, QueryIntent } from '../types/api';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  intent?: QueryIntent;
  citations?: Citation[];
  dataSummary?: Record<string, any> | null;
  timestamp: string;
}

const SUGGESTED_PROMPTS = [
  "What is Rule 6(1)(e) regarding MRP format?",
  "What is the official SOP for Edible Oils net quantity measurement?",
  "शुद्ध मात्रा घोषणा के क्या नियम हैं?",
  "What is our current compliance rate and total scans in the database?",
  "Who are the top non-compliant brands?",
];

export const ChatAssistant: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      sender: 'assistant',
      text: "Namaste! I am the official **DoCA Legal Metrology Assistant**. I answer questions strictly grounded in the *Legal Metrology (Packaged Commodities) Rules, 2011*, official DoCA gazettes, and real-time database audit statistics.\n\nHow may I assist your inspection today?",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);
  const [inputPrompt, setInputPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputPrompt).trim();
    if (!query || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputPrompt('');
    setIsLoading(true);

    try {
      const response: ChatResponse = await chatApi.sendMessage({ message: query });
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: response.reply,
        intent: response.intent,
        citations: response.citations,
        dataSummary: response.data_summary,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'assistant',
        text: err?.response?.data?.detail || "I encountered an error retrieving grounded legal data. Please verify your officer credentials and try again.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto flex flex-col h-[calc(100vh-140px)] min-h-[550px] glass-panel rounded-2xl border border-slate-800 overflow-hidden animate-fade-in">
      {/* Chat Header */}
      <div className="p-4 border-b border-slate-800 bg-slate-900/80 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-600 flex items-center justify-center text-white shadow-glow">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-sm font-bold text-white font-display">
                DoCA Grounded Legal Metrology Assistant
              </h2>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                100% Grounded
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Official PCR 2011 Gazettes & Database Analytics
            </p>
          </div>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex items-start space-x-3 ${
              msg.sender === 'user' ? 'flex-row-reverse space-x-reverse' : 'flex-row'
            }`}
          >
            {/* Avatar */}
            <div
              className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                msg.sender === 'user'
                  ? 'bg-brand-600 text-white'
                  : 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40'
              }`}
            >
              {msg.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
            </div>

            {/* Bubble */}
            <div
              className={`max-w-[85%] sm:max-w-[75%] rounded-2xl p-4 text-xs sm:text-sm leading-relaxed space-y-2 ${
                msg.sender === 'user'
                  ? 'bg-brand-600 text-white rounded-tr-none'
                  : 'bg-slate-900 border border-slate-800 text-slate-200 rounded-tl-none'
              }`}
            >
              {/* Intent Badge */}
              {msg.intent && msg.intent !== 'UNKNOWN' && (
                <div className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full bg-slate-950/80 border border-slate-700/80 text-[10px] font-semibold text-brand-300 mb-1">
                  {msg.intent === 'RULE_LOOKUP' && <BookOpen className="w-3 h-3 text-brand-400" />}
                  {msg.intent === 'DATA_QUERY' && <Database className="w-3 h-3 text-indigo-400" />}
                  {msg.intent === 'HYBRID' && <Sparkles className="w-3 h-3 text-amber-400" />}
                  <span>{msg.intent.replace(/_/g, ' ')}</span>
                </div>
              )}

              {/* Message Text with simple markdown formatting */}
              <div className="whitespace-pre-line">
                {msg.text}
              </div>

              {/* Citations Box */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-3 pt-2.5 border-t border-slate-800/80 space-y-2">
                  <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                    Official Statutory Citations:
                  </span>
                  {msg.citations.map((c, i) => (
                    <div key={i} className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800 space-y-1 text-[11px]">
                      <div className="flex items-center justify-between font-semibold text-brand-300">
                        <span>{c.official_legal_reference}</span>
                        {c.rule_id && <span className="text-[9px] font-mono text-slate-500">{c.rule_id}</span>}
                      </div>
                      {c.source_pdf && (
                        <div className="flex items-center space-x-1 text-[10px] text-indigo-300 font-mono">
                          <FileText className="w-3 h-3" />
                          <span>Document: {c.source_pdf}</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <span className="block text-[10px] text-slate-500 text-right mt-1">
                {msg.timestamp}
              </span>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 rounded-xl bg-indigo-600/30 text-indigo-300 border border-indigo-500/40 flex items-center justify-center">
              <Bot className="w-4 h-4" />
            </div>
            <div className="p-3.5 rounded-2xl bg-slate-900 border border-slate-800 rounded-tl-none flex items-center space-x-2 text-xs text-slate-400">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-brand-400" />
              <span>Searching DoCA official gazettes & scan database...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested Prompts */}
      <div className="px-4 py-2 bg-slate-950/60 border-t border-slate-800/60 flex items-center space-x-2 overflow-x-auto no-scrollbar">
        <span className="text-[10px] font-semibold text-slate-500 flex-shrink-0 flex items-center">
          <HelpCircle className="w-3 h-3 mr-1" /> Prompts:
        </span>
        {SUGGESTED_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            onClick={() => handleSendMessage(prompt)}
            className="flex-shrink-0 px-2.5 py-1 rounded-full bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-brand-500/40 text-[11px] text-slate-300 transition-colors"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Input Box */}
      <div className="p-3 sm:p-4 bg-slate-900/90 border-t border-slate-800 flex items-center space-x-2">
        <input
          type="text"
          value={inputPrompt}
          onChange={(e) => setInputPrompt(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') handleSendMessage();
          }}
          placeholder="Ask about Rule 6(1), MRP, net quantity, Hindi provisions, or audit statistics..."
          className="flex-1 bg-slate-950 border border-slate-700/80 rounded-xl px-4 py-2.5 text-xs sm:text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-brand-500"
        />
        <button
          onClick={() => handleSendMessage()}
          disabled={!inputPrompt.trim() || isLoading}
          className="p-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white shadow-glow disabled:opacity-40 transition-all active:scale-95"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
