import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  Camera, 
  Sparkles, 
  Settings2, 
  RefreshCw, 
  ShieldCheck, 
  Cpu,
  AlertCircle,
  Package,
  ShoppingBag,
  X,
  CheckCircle2,
  Zap
} from 'lucide-react';
import { scanApi } from '../services/api';
import type { AnalyzeScanResponse } from '../types/api';

interface ScanUploadProps {
  onScanComplete: (result: AnalyzeScanResponse, originalImageSrc: string) => void;
}

export const ScanUpload: React.FC<ScanUploadProps> = ({ onScanComplete }) => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [useEnsemble, setUseEnsemble] = useState(true);
  const [strategy, setStrategy] = useState<string>('standard');
  const [brandName, setBrandName] = useState<string>('');
  const [inputType, setInputType] = useState<'physical_package' | 'ecommerce_listing'>('physical_package');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const addFiles = (newFiles: File[]) => {
    if (newFiles.length === 0) return;
    const urls = newFiles.map((f) => URL.createObjectURL(f));
    setSelectedFiles((prev) => [...prev, ...newFiles]);
    setPreviewUrls((prev) => [...prev, ...urls]);
    stopCamera();
    setError(null);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      addFiles(Array.from(e.target.files));
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      addFiles(Array.from(e.dataTransfer.files));
    }
  };

  const removeImage = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setPreviewUrls((prev) => prev.filter((_, i) => i !== index));
  };

  const clearAllImages = () => {
    setSelectedFiles([]);
    setPreviewUrls([]);
  };

  const startCamera = async () => {
    try {
      setError(null);
      setIsCameraActive(true);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch {
      setError('Unable to access camera. Please allow camera permissions or upload image file(s).');
      setIsCameraActive(false);
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsCameraActive(false);
  };

  const captureSnapshot = () => {
    if (!videoRef.current) return;
    const video = videoRef.current;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob((blob) => {
        if (blob) {
          const snapshotFile = new File([blob], `camera_panel_${selectedFiles.length + 1}.jpg`, { type: 'image/jpeg' });
          addFiles([snapshotFile]);
        }
      }, 'image/jpeg', 0.95);
    }
  };

  const handleAnalyze = async () => {
    if (selectedFiles.length === 0 && previewUrls.length === 0) {
      setError('Please upload at least one package image or capture a scan first.');
      return;
    }
    setError(null);
    setIsAnalyzing(true);
    try {
      const response = await scanApi.analyzeImage(selectedFiles, {
        use_ensemble: useEnsemble,
        preprocessing_strategy: strategy,
        brand_name: brandName.trim() || undefined,
        persist: true,
        input_type: inputType,
      });
      onScanComplete(response, previewUrls[0] || '');
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      const msg = typeof detail === 'string' ? detail : (typeof detail === 'object' ? JSON.stringify(detail) : (err?.message || 'Analysis failed. Ensure the images are clear package or product listing images and try again.'));
      setError(msg);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const isEcommerce = inputType === 'ecommerce_listing';

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6 animate-fade-in">

      {/* ── Hero Banner ── */}
      <div className="relative overflow-hidden rounded-2xl border border-white/5 hero-gradient p-6 sm:p-8">
        {/* Background decoration */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-24 -right-24 w-64 h-64 rounded-full opacity-[0.04]"
            style={{ background: 'radial-gradient(circle, #0ea5e9, transparent 70%)' }} />
          <div className="absolute -bottom-20 -left-20 w-48 h-48 rounded-full opacity-[0.04]"
            style={{ background: 'radial-gradient(circle, #6366f1, transparent 70%)' }} />
        </div>

        <div className="relative space-y-3 text-center max-w-2xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold border"
            style={{ background: 'rgba(14,165,233,0.08)', borderColor: 'rgba(14,165,233,0.2)', color: '#7dd3fc' }}
          >
            <Sparkles className="w-3.5 h-3.5" />
            {isEcommerce
              ? 'E-Commerce PDP Compliance · Marketplace Screenshots & Multi-Image Carousels'
              : 'Multi-Image Scan · Upload 2+ Panels (Front, Back, Sides)'}
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white font-display leading-tight">
            {isEcommerce ? (
              <>E-Commerce <span className="gradient-text">Marketplace</span> Compliance</>
            ) : (
              <>Statutory <span className="gradient-text">Compliance</span> Scanner</>
            )}
          </h1>

          <p className="text-sm text-slate-400 leading-relaxed">
            {isEcommerce
              ? 'Upload one or more e-commerce listing screenshots or product carousel images. The engine extracts key details and checks them for compliance.'
              : 'Upload one or more product panel images (e.g. front & back). The engine merges extracted fields and checks all mandatory declarations.'}
          </p>
        </div>
      </div>

      {/* ── Mode Selector ── */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 max-w-lg mx-auto">
        <button
          type="button"
          onClick={() => setInputType('physical_package')}
          className={`flex-1 flex items-center justify-center gap-3 py-3 px-5 rounded-2xl font-semibold text-sm transition-all duration-200 border ${
            !isEcommerce
              ? 'bg-sky-500/15 text-sky-200 border-sky-500/40 shadow-lg shadow-sky-500/10'
              : 'bg-white/3 text-slate-400 border-white/5 hover:bg-white/6 hover:text-slate-300'
          }`}
        >
          <Package className={`w-4 h-4 ${!isEcommerce ? 'text-sky-400' : ''}`} />
          <span>Scan Physical Package</span>
          {!isEcommerce && <CheckCircle2 className="w-4 h-4 text-sky-400 ml-auto" />}
        </button>
        <button
          type="button"
          onClick={() => setInputType('ecommerce_listing')}
          className={`flex-1 flex items-center justify-center gap-3 py-3 px-5 rounded-2xl font-semibold text-sm transition-all duration-200 border ${
            isEcommerce
              ? 'bg-amber-500/15 text-amber-200 border-amber-500/40 shadow-lg shadow-amber-500/10'
              : 'bg-white/3 text-slate-400 border-white/5 hover:bg-white/6 hover:text-slate-300'
          }`}
        >
          <ShoppingBag className={`w-4 h-4 ${isEcommerce ? 'text-amber-400' : ''}`} />
          <span>E-Commerce Listing</span>
          {isEcommerce && <CheckCircle2 className="w-4 h-4 text-amber-400 ml-auto" />}
        </button>
      </div>

      {/* ── Main Scanner Grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">

        {/* Left: Image Input Panel */}
        <div className="lg:col-span-8 glass rounded-2xl border border-white/5 overflow-hidden">
          {isCameraActive ? (
            <div className="relative w-full h-[380px] sm:h-[450px] bg-black flex items-center justify-center">
              <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-contain" />
              {/* Scan overlay */}
              <div className="absolute inset-0 scan-overlay pointer-events-none">
                <div className="absolute inset-8 border border-dashed border-sky-400/60 rounded-xl" />
                <div className="absolute top-8 left-8 w-6 h-6 border-t-2 border-l-2 border-sky-400 rounded-tl-lg" />
                <div className="absolute top-8 right-8 w-6 h-6 border-t-2 border-r-2 border-sky-400 rounded-tr-lg" />
                <div className="absolute bottom-8 left-8 w-6 h-6 border-b-2 border-l-2 border-sky-400 rounded-bl-lg" />
                <div className="absolute bottom-8 right-8 w-6 h-6 border-b-2 border-r-2 border-sky-400 rounded-br-lg" />
              </div>
              <div className="absolute top-3 left-3 flex items-center gap-2 bg-black/70 backdrop-blur-sm px-3 py-1.5 rounded-lg border border-white/10">
                <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
                <span className="text-xs text-white font-semibold">LIVE CAM</span>
              </div>
              <div className="absolute bottom-5 inset-x-0 flex justify-center gap-3">
                <button
                  onClick={captureSnapshot}
                  className="px-6 py-2.5 rounded-full text-white font-bold text-sm flex items-center gap-2 transition-all active:scale-95 shadow-lg"
                  style={{ background: 'linear-gradient(135deg, #0171c7, #4f46e5)', boxShadow: '0 4px 20px rgba(14,165,233,0.4)' }}
                >
                  <Camera className="w-4 h-4" />
                  Capture ({selectedFiles.length} saved)
                </button>
                <button
                  onClick={stopCamera}
                  className="px-5 py-2.5 rounded-full bg-white/10 hover:bg-white/15 text-slate-200 text-sm font-medium border border-white/10 transition-colors"
                >
                  Done
                </button>
              </div>
            </div>
          ) : previewUrls.length > 0 ? (
            <div className="p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-sky-400 animate-pulse" />
                  <span className="text-xs font-bold text-sky-300">
                    {previewUrls.length} {previewUrls.length === 1 ? 'Image' : 'Images'} Ready
                    {' '}· {isEcommerce ? 'Listing Carousel Fusion' : 'Multi-Panel Fusion'}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="btn-ghost text-xs"
                  >
                    + Add More
                  </button>
                  <button
                    type="button"
                    onClick={clearAllImages}
                    className="px-3 py-1.5 rounded-lg bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/20 text-rose-300 text-xs font-semibold transition-all"
                  >
                    Clear All
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 max-h-[380px] overflow-y-auto">
                {previewUrls.map((url, idx) => (
                  <div key={idx} className="relative group rounded-xl overflow-hidden border border-white/5 bg-slate-900 h-36 flex items-center justify-center glass-hover">
                    <img src={url} alt={`Panel ${idx + 1}`} className="w-full h-full object-contain" />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="absolute top-2 left-2 px-2 py-0.5 rounded-md bg-black/70 backdrop-blur-sm text-[10px] font-bold text-slate-200 border border-white/10">
                      {isEcommerce ? `IMG #${idx + 1}` : `Panel #${idx + 1}`}
                    </div>
                    <button
                      type="button"
                      onClick={() => removeImage(idx)}
                      className="absolute top-2 right-2 w-6 h-6 rounded-full bg-rose-500/90 text-white font-bold text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-lg"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
                <label
                  className="relative group rounded-xl border-2 border-dashed border-white/10 hover:border-sky-500/40 h-36 flex flex-col items-center justify-center cursor-pointer transition-all hover:bg-sky-500/5"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <UploadCloud className="w-6 h-6 text-slate-600 group-hover:text-sky-400 transition-colors mb-1" />
                  <span className="text-[11px] text-slate-600 group-hover:text-sky-400 font-medium transition-colors">Add Panel</span>
                </label>
              </div>
            </div>
          ) : (
            <div
              onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`w-full h-[380px] sm:h-[450px] flex flex-col items-center justify-center p-6 text-center cursor-pointer transition-all duration-300 ${
                isDragOver
                  ? 'bg-sky-500/10 border-sky-400/60'
                  : 'bg-transparent hover:bg-white/2'
              }`}
            >
              <input ref={fileInputRef} type="file" accept="image/*" multiple onChange={handleFileChange} className="hidden" />

              {/* Upload Icon */}
              <div className={`relative w-20 h-20 rounded-2xl flex items-center justify-center mb-5 transition-all duration-300 ${
                isDragOver ? 'scale-110' : 'group-hover:scale-105'
              }`}
                style={{ background: 'linear-gradient(135deg, rgba(1,113,199,0.15), rgba(79,70,229,0.15))', border: '1px solid rgba(14,165,233,0.2)' }}
              >
                <UploadCloud className={`w-9 h-9 transition-colors ${isDragOver ? 'text-sky-300' : 'text-sky-500'}`} />
                <div className="absolute inset-0 rounded-2xl"
                  style={isDragOver ? { boxShadow: '0 0 40px rgba(14,165,233,0.3)' } : {}} />
              </div>

              <h3 className="text-lg font-semibold text-slate-200 mb-1">
                {isDragOver ? 'Drop your images here' : isEcommerce ? 'Drop e-commerce listing screenshots' : 'Drop package panel images here'}
              </h3>
              <p className="text-sm text-slate-500 max-w-xs">
                {isEcommerce
                  ? 'Upload screenshots of product page, specification table, or carousel images.'
                  : 'Select front, back, or side panels simultaneously. Supports JPG, PNG, WEBP.'}
              </p>

              <div className="flex items-center gap-4 mt-7" onClick={(e) => e.stopPropagation()}>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="btn-primary text-xs !py-2.5"
                >
                  <UploadCloud className="w-3.5 h-3.5" />
                  Browse Files
                </button>
                <span className="text-slate-600 text-xs">or</span>
                <button
                  type="button"
                  onClick={startCamera}
                  className="btn-ghost text-xs"
                >
                  <Camera className="w-3.5 h-3.5" />
                  Open Camera
                </button>
              </div>

              {/* Feature Tags */}
              <div className="flex flex-wrap items-center justify-center gap-2 mt-6">
                {['JPG', 'PNG', 'WEBP', 'Multi-panel'].map(t => (
                  <span key={t} className="px-2.5 py-1 rounded-lg bg-white/4 text-slate-500 text-[11px] font-medium border border-white/5">{t}</span>
                ))}
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="mx-4 mb-4 p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/25 flex items-start gap-2.5 text-rose-300 text-xs animate-fade-in">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Right: Inspection Configuration */}
        <div className="lg:col-span-4 glass rounded-2xl border border-white/5 p-5 flex flex-col gap-5">
          
          {/* Header */}
          <div className="flex items-center gap-2.5 pb-4 border-b border-white/5">
            <div className="w-8 h-8 rounded-xl flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, rgba(14,165,233,0.15), rgba(99,102,241,0.15))', border: '1px solid rgba(14,165,233,0.2)' }}
            >
              <Settings2 className="w-4 h-4 text-sky-400" />
            </div>
            <h3 className="text-sm font-bold text-slate-100 font-display">Inspection Parameters</h3>
          </div>

          <div className="flex-1 space-y-4">
            {/* Advanced Scan Toggle */}
            <div className="p-4 rounded-xl border border-white/5 hover:border-sky-500/20 transition-colors"
              style={{ background: 'rgba(14,165,233,0.03)' }}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Cpu className="w-4 h-4 text-indigo-400" />
                  <span className="text-xs font-semibold text-slate-200">Advanced Scanning</span>
                </div>
                {/* Premium Toggle Switch */}
                <button
                  onClick={() => setUseEnsemble(!useEnsemble)}
                  className={`relative w-10 h-5.5 rounded-full transition-all duration-300 flex items-center ${
                    useEnsemble ? 'bg-sky-500' : 'bg-slate-700'
                  }`}
                  style={{ height: '22px', width: '40px' }}
                >
                  <span className={`absolute w-4 h-4 bg-white rounded-full shadow transition-all duration-300 ${useEnsemble ? 'left-[22px]' : 'left-[2px]'}`} />
                </button>
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Combines multiple recognition engines for higher accuracy across different fonts, sizes, and layouts.
              </p>
            </div>

            {/* Preprocessing Strategy */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-300">
                Image Rectification & Preprocessing
              </label>
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
                className="w-full rounded-xl px-3.5 py-2.5 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-sky-500/50 transition-all"
                style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
              >
                <option value="standard">Standard (Auto Adaptive CLAHE)</option>
                <option value="high_contrast">High Contrast (Glare Suppression)</option>
                <option value="denoise">Bilateral Denoise (Curved Packaging)</option>
                <option value="binary">Otsu Binarization (Fine Print)</option>
              </select>
            </div>

            {/* Brand Authenticity */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-300">
                Brand Authenticity Check
              </label>
              <input
                type="text"
                value={brandName}
                onChange={(e) => setBrandName(e.target.value)}
                placeholder="e.g. Amul, Fortune, Parle-G (Optional)"
                className="w-full rounded-xl px-3.5 py-2.5 text-xs text-slate-200 placeholder:text-slate-600 focus:outline-none focus:ring-1 focus:ring-sky-500/50 transition-all"
                style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)' }}
              />
              <p className="text-[11px] text-slate-600">
                Visually verifies the product matches the known brand reference.
              </p>
            </div>

            {/* Feature Preview Chips */}
            <div className="grid grid-cols-2 gap-2">
              {[
                { label: 'MRP Validation', active: true },
                { label: 'Net Qty Check', active: true },
                { label: 'Font Size Rule 9', active: true },
                { label: 'Brand Auth', active: !!brandName },
              ].map(f => (
                <div key={f.label} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-[11px] font-medium transition-all ${
                  f.active ? 'bg-emerald-500/8 border-emerald-500/20 text-emerald-400' : 'bg-white/3 border-white/5 text-slate-600'
                }`}>
                  <div className={`w-1.5 h-1.5 rounded-full ${f.active ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                  {f.label}
                </div>
              ))}
            </div>
          </div>

          {/* Analyze CTA */}
          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing || (selectedFiles.length === 0 && previewUrls.length === 0)}
            className="w-full py-3.5 px-4 rounded-xl font-bold text-sm text-white flex items-center justify-center gap-2.5 transition-all active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed relative overflow-hidden"
            style={{
              background: isAnalyzing ? 'rgba(1,113,199,0.5)' : 'linear-gradient(135deg, #0171c7, #4f46e5)',
              boxShadow: selectedFiles.length > 0 ? '0 6px 25px rgba(14,165,233,0.35)' : 'none'
            }}
          >
            {isAnalyzing ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Running Compliance Engine...</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4" />
                <span>
                  {isEcommerce ? 'Verify E-Commerce Listing' : 'Verify Package Compliance'}
                </span>
                <Zap className="w-3.5 h-3.5 ml-auto opacity-60" />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
