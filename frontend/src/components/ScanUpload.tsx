import React, { useState, useRef } from 'react';
import { 
  UploadCloud, 
  Camera, 
  Sparkles, 
  Settings2, 
  RefreshCw, 
  ShieldCheck, 
  Cpu,
  AlertCircle
} from 'lucide-react';
import { scanApi } from '../services/api';
import type { AnalyzeScanResponse } from '../types/api';

interface ScanUploadProps {
  onScanComplete: (result: AnalyzeScanResponse, originalImageSrc: string) => void;
}

export const ScanUpload: React.FC<ScanUploadProps> = ({ onScanComplete }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isCameraActive, setIsCameraActive] = useState(false);
  const [useEnsemble, setUseEnsemble] = useState(true);
  const [strategy, setStrategy] = useState<string>('standard');
  const [brandName, setBrandName] = useState<string>('');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Handle file select
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      stopCamera();
      setError(null);
    }
  };

  // Drag and drop
  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      stopCamera();
      setError(null);
    }
  };

  // Start Camera
  const startCamera = async () => {
    try {
      setError(null);
      setIsCameraActive(true);
      setPreviewUrl(null);
      setSelectedFile(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
    } catch {
      setError('Unable to access camera. Please allow camera permissions or upload an image file.');
      setIsCameraActive(false);
    }
  };

  // Stop Camera
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsCameraActive(false);
  };

  // Capture Snapshot from Camera
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
          const file = new File([blob], 'camera_capture.jpg', { type: 'image/jpeg' });
          setSelectedFile(file);
          setPreviewUrl(canvas.toDataURL('image/jpeg'));
          stopCamera();
        }
      }, 'image/jpeg', 0.95);
    }
  };

  // Trigger Analysis
  const handleAnalyze = async () => {
    if (!selectedFile && !previewUrl) {
      setError('Please upload an image or capture a package scan first.');
      return;
    }

    setError(null);
    setIsAnalyzing(true);

    try {
      let fileToUpload: File | Blob = selectedFile!;
      if (!selectedFile && previewUrl) {
        // Fetch blob from data URL
        const res = await fetch(previewUrl);
        fileToUpload = await res.blob();
      }

      const response = await scanApi.analyzeImage(fileToUpload, {
        use_ensemble: useEnsemble,
        preprocessing_strategy: strategy,
        brand_name: brandName.trim() || undefined,
        persist: true,
      });

      onScanComplete(response, previewUrl || '');
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          'Analysis failed. Ensure the image is a clear package declaration image and try again.'
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6 animate-fade-in">
      {/* Hero Header */}
      <div className="text-center space-y-2">
        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-300 text-xs font-semibold">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Multi-Engine OCR Ensemble • Orientation Correction • DINOv2 Authenticity</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white font-display">
          Statutory Package Compliance Scanner
        </h1>
        <p className="text-sm text-slate-400 max-w-2xl mx-auto">
          Capture or upload pre-packaged commodity labels. The engine validates statutory declarations against 
          the <span className="text-brand-300 font-semibold">Legal Metrology (Packaged Commodities) Rules, 2011</span> and official DoCA gazettes.
        </p>
      </div>

      {/* Main Scanner Container */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Input Viewport */}
        <div className="lg:col-span-8 glass-panel rounded-2xl p-4 sm:p-6 flex flex-col justify-between min-h-[420px]">
          {isCameraActive ? (
            <div className="relative w-full h-[360px] sm:h-[420px] rounded-xl overflow-hidden bg-black flex items-center justify-center border border-slate-800">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-contain"
              />
              <div className="absolute inset-0 border-2 border-brand-400/40 rounded-xl pointer-events-none flex items-center justify-center">
                <div className="w-64 h-64 border border-dashed border-brand-400/80 rounded-lg animate-pulse" />
              </div>
              <div className="absolute bottom-4 inset-x-0 flex justify-center space-x-4">
                <button
                  onClick={captureSnapshot}
                  className="px-6 py-2.5 rounded-full bg-brand-600 hover:bg-brand-500 text-white font-semibold text-sm shadow-glow flex items-center space-x-2 transition-all active:scale-95"
                >
                  <Camera className="w-4 h-4" />
                  <span>Capture Snapshot</span>
                </button>
                <button
                  onClick={stopCamera}
                  className="px-4 py-2.5 rounded-full bg-slate-800/90 hover:bg-slate-700 text-slate-200 font-medium text-xs transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : previewUrl ? (
            <div className="relative w-full h-[360px] sm:h-[420px] rounded-xl overflow-hidden bg-slate-950 border border-slate-800 flex items-center justify-center group">
              <img
                src={previewUrl}
                alt="Package preview"
                className="w-full h-full object-contain"
              />
              <div className="absolute top-3 right-3 flex items-center space-x-2">
                <button
                  onClick={() => {
                    setPreviewUrl(null);
                    setSelectedFile(null);
                  }}
                  className="px-3 py-1.5 rounded-lg bg-slate-900/80 backdrop-blur-md border border-slate-700 hover:bg-rose-600/80 text-xs text-slate-200 hover:text-white transition-all"
                >
                  Change Image
                </button>
              </div>
            </div>
          ) : (
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className="w-full h-[360px] sm:h-[420px] border-2 border-dashed border-slate-700 hover:border-brand-500/60 rounded-xl flex flex-col items-center justify-center p-6 text-center cursor-pointer transition-all bg-slate-900/40 hover:bg-slate-900/70 group"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileChange}
                className="hidden"
              />
              <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 text-brand-400 flex items-center justify-center mb-4 group-hover:scale-110 group-hover:shadow-glow transition-all">
                <UploadCloud className="w-8 h-8" />
              </div>
              <p className="text-base font-semibold text-slate-200">
                Drag and drop your package image here
              </p>
              <p className="text-xs text-slate-400 mt-1">
                Supports JPG, PNG, WEBP high-resolution packaging labels
              </p>

              <div className="flex items-center space-x-3 mt-6">
                <span className="text-xs text-slate-500">or</span>
              </div>

              <div className="flex items-center space-x-3 mt-4" onClick={(e) => e.stopPropagation()}>
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs font-semibold text-slate-200 transition-colors"
                >
                  Browse Files
                </button>
                <button
                  type="button"
                  onClick={startCamera}
                  className="px-4 py-2 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-xs font-semibold text-indigo-300 flex items-center space-x-1.5 transition-colors"
                >
                  <Camera className="w-3.5 h-3.5" />
                  <span>Open Camera</span>
                </button>
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="mt-4 p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 flex items-start space-x-2 text-rose-300 text-xs">
              <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Right: Inspection Configuration Sidebar */}
        <div className="lg:col-span-4 glass-panel rounded-2xl p-5 flex flex-col justify-between space-y-5">
          <div className="space-y-4">
            <div className="flex items-center space-x-2 pb-3 border-b border-slate-800">
              <Settings2 className="w-4 h-4 text-brand-400" />
              <h3 className="text-sm font-bold text-slate-200 font-display">
                Inspection Parameters
              </h3>
            </div>

            {/* OCR Ensemble Switch */}
            <div className="p-3.5 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Cpu className="w-4 h-4 text-indigo-400" />
                  <span className="text-xs font-semibold text-slate-200">OCR Ensemble</span>
                </div>
                <input
                  type="checkbox"
                  checked={useEnsemble}
                  onChange={(e) => setUseEnsemble(e.target.checked)}
                  className="w-4 h-4 accent-brand-500 rounded cursor-pointer"
                />
              </div>
              <p className="text-[11px] text-slate-400">
                Fuses PaddleOCR, EasyOCR & Tesseract with IoU &gt; 0.5 text clustering & spatial reading order.
              </p>
            </div>

            {/* Preprocessing Strategy */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-300">
                Image Rectification & Preprocessing
              </label>
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
              >
                <option value="standard">Standard (Auto Adaptive CLAHE)</option>
                <option value="high_contrast">High Contrast (Glare Suppression)</option>
                <option value="denoise">Bilateral Denoise (Curved Packaging)</option>
                <option value="binary">Otsu Binarization (Fine Print)</option>
              </select>
            </div>

            {/* Reference Brand Check (DINOv2) */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-300">
                DINOv2 Visual Authenticity Check
              </label>
              <input
                type="text"
                value={brandName}
                onChange={(e) => setBrandName(e.target.value)}
                placeholder="e.g. Amul, Fortune, Parle-G (Optional)"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-brand-500"
              />
              <p className="text-[10px] text-slate-500">
                Compares embeddings against registered brand trade-dress references.
              </p>
            </div>
          </div>

          {/* Action Button */}
          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing || (!selectedFile && !previewUrl)}
            className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-brand-600 via-indigo-600 to-brand-500 hover:from-brand-500 hover:to-indigo-500 text-white font-bold text-sm shadow-glow transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
          >
            {isAnalyzing ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Running Compliance Verification...</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4" />
                <span>Verify Package Compliance</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
