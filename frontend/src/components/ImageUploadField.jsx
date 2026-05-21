import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Upload, X, ImageIcon, Loader2, AlertCircle } from 'lucide-react';
import { cn } from '@/lib';
import { uploadImage } from '../services/apiService';

const ALLOWED_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
const MAX_SIZE_MB = 5;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

/**
 * ImageUploadField
 *
 * A reusable drag-and-drop / click-to-upload component that:
 *  1. Validates file type and size client-side
 *  2. Shows a local preview immediately
 *  3. Uploads to the backend POST /upload/image
 *  4. Calls onUploadComplete(url) with the public Supabase URL
 *
 * Props:
 *  - onUploadComplete: (url: string) => void    — called with the final public URL
 *  - entityType: 'property' | 'building' | 'unit'
 *  - currentImageUrl?: string                   — existing image (edit mode)
 *  - label?: string
 *  - disabled?: boolean
 */
function ImageUploadField({
    onUploadComplete,
    onUploadStart,          // NEW — called when upload begins (for parent to disable submit)
    entityType = 'misc',
    currentImageUrl = '',
    label = 'Cover Image',
    disabled = false,
}) {
    const [preview, setPreview] = useState(currentImageUrl || null);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState('');
    const [isDragging, setIsDragging] = useState(false);
    const inputRef = useRef(null);

    // Validate file before touching the server
    const validate = (file) => {
        if (!ALLOWED_TYPES.includes(file.type)) {
            return 'Only JPG, PNG, and WebP images are allowed.';
        }
        if (file.size > MAX_SIZE_BYTES) {
            return `File too large (${(file.size / 1024 / 1024).toFixed(1)} MB). Max: ${MAX_SIZE_MB} MB.`;
        }
        return null;
    };

    const processFile = useCallback(async (file) => {
        if (!file) return;

        const validationError = validate(file);
        if (validationError) {
            setError(validationError);
            return;
        }

        // Local preview immediately — no wait
        const localUrl = URL.createObjectURL(file);
        setPreview(localUrl);
        setError('');
        setUploading(true);
        onUploadStart?.();  // notify parent upload has begun

        try {
            const { url } = await uploadImage(file, entityType);
            onUploadComplete(url);
            // Replace blob URL with permanent Supabase URL
            setPreview(url);
        } catch (err) {
            setError(err.message || 'Upload failed. Please try again.');
            // Revert preview to whatever was there before (currentImageUrl or nothing)
            setPreview(currentImageUrl || null);
            onUploadComplete(''); // clear in parent so old URL isn't accidentally submitted
        } finally {
            setUploading(false);
        }
    }, [entityType, currentImageUrl, onUploadComplete]);

    const handleFileChange = (e) => {
        const file = e.target.files?.[0];
        if (file) processFile(file);
        // Reset input so same file can be re-selected after an error
        e.target.value = '';
    };

    const handleDrop = (e) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files?.[0];
        if (file) processFile(file);
    };

    const clearImage = (e) => {
        e.stopPropagation();
        setPreview(null);
        setError('');
        onUploadComplete('');
        if (inputRef.current) inputRef.current.value = '';
    };

    return (
        <div className="space-y-1.5">
            {label && (
                <label className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    <ImageIcon className="w-3.5 h-3.5" />
                    {label}
                </label>
            )}

            {/* Drop Zone */}
            <div
                onClick={() => !disabled && !uploading && inputRef.current?.click()}
                onDragOver={(e) => { e.preventDefault(); if (!disabled) setIsDragging(true); }}
                onDragLeave={() => setIsDragging(false)}
                onDrop={handleDrop}
                className={cn(
                    'relative rounded-xl border-2 border-dashed transition-all duration-200 overflow-hidden',
                    'cursor-pointer select-none',
                    isDragging ? 'border-primary bg-primary/5 scale-[1.01]' : 'border-border hover:border-primary/50 hover:bg-secondary/50',
                    (disabled || uploading) && 'pointer-events-none opacity-70',
                    preview ? 'h-40' : 'h-32'
                )}
            >
                <AnimatePresence mode="wait">
                    {preview ? (
                        /* Preview state */
                        <motion.div
                            key="preview"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="absolute inset-0"
                        >
                            <img
                                src={preview}
                                alt="Preview"
                                className="w-full h-full object-cover"
                                onError={() => setPreview(null)}
                            />
                            {/* Overlay */}
                            <div className="absolute inset-0 bg-black/40 opacity-0 hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
                                <span className="text-white text-xs font-medium bg-black/50 px-3 py-1.5 rounded-full flex items-center gap-1.5">
                                    <Upload className="w-3.5 h-3.5" />
                                    Replace
                                </span>
                            </div>
                            {/* Clear button */}
                            {!uploading && (
                                <button
                                    type="button"
                                    onClick={clearImage}
                                    className="absolute top-2 right-2 p-1 rounded-full bg-black/60 text-white hover:bg-red-500 transition-colors"
                                >
                                    <X className="w-3.5 h-3.5" />
                                </button>
                            )}
                            {/* Upload overlay */}
                            {uploading && (
                                <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
                                    <Loader2 className="w-6 h-6 text-white animate-spin" />
                                    <span className="ml-2 text-white text-sm font-medium">Uploading…</span>
                                </div>
                            )}
                        </motion.div>
                    ) : (
                        /* Empty / prompt state */
                        <motion.div
                            key="empty"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="flex flex-col items-center justify-center h-full gap-2 p-4"
                        >
                            {uploading ? (
                                <>
                                    <Loader2 className="w-7 h-7 text-primary animate-spin" />
                                    <span className="text-sm text-muted-foreground">Uploading…</span>
                                </>
                            ) : (
                                <>
                                    <Upload className={cn('w-7 h-7 transition-colors', isDragging ? 'text-primary' : 'text-muted-foreground')} />
                                    <div className="text-center">
                                        <p className="text-sm font-medium text-foreground">
                                            {isDragging ? 'Drop to upload' : 'Click or drag to upload'}
                                        </p>
                                        <p className="text-xs text-muted-foreground mt-0.5">
                                            JPG, PNG, WebP · max {MAX_SIZE_MB} MB
                                        </p>
                                    </div>
                                </>
                            )}
                        </motion.div>
                    )}
                </AnimatePresence>

                <input
                    ref={inputRef}
                    type="file"
                    accept="image/jpeg,image/png,image/webp"
                    onChange={handleFileChange}
                    className="sr-only"
                    disabled={disabled || uploading}
                />
            </div>

            {/* Error */}
            <AnimatePresence>
                {error && (
                    <motion.p
                        initial={{ opacity: 0, y: -4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="flex items-center gap-1.5 text-xs text-red-500"
                    >
                        <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                        {error}
                    </motion.p>
                )}
            </AnimatePresence>
        </div>
    );
}

export default ImageUploadField;
