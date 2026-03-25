import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Phone, PhoneCall, PhoneOff, X } from 'lucide-react';
import { makeOutboundCall } from '../services/apiService';

const STATUS = {
    IDLE: 'idle',
    CALLING: 'calling',
    SUCCESS: 'success',
    ERROR: 'error',
};

export default function OutboundCallButton() {
    const [open, setOpen] = useState(false);
    const [number, setNumber] = useState('+91');
    const [status, setStatus] = useState(STATUS.IDLE);
    const [errorMsg, setErrorMsg] = useState('');
    const inputRef = useRef(null);

    // Focus input when panel opens
    useEffect(() => {
        if (open) {
            setTimeout(() => inputRef.current?.focus(), 150);
        }
    }, [open]);

    // Reset state when panel closes
    function handleClose() {
        setOpen(false);
        setStatus(STATUS.IDLE);
        setErrorMsg('');
        setNumber('+91');
    }

    function handleToggle() {
        if (open) handleClose();
        else setOpen(true);
    }

    async function handleCall() {
        const trimmed = number.trim();
        if (!trimmed) return;

        // Basic E.164 validation: starts with + and has 7–15 digits after it
        if (!/^\+\d{7,15}$/.test(trimmed)) {
            setStatus(STATUS.ERROR);
            setErrorMsg('Enter a valid number: +[country code][number], e.g. +919876543210');
            return;
        }

        setStatus(STATUS.CALLING);
        setErrorMsg('');

        try {
            const result = await makeOutboundCall(trimmed);
            console.log('[Outbound Call]', result);
            setStatus(STATUS.SUCCESS);
        } catch (err) {
            setStatus(STATUS.ERROR);
            setErrorMsg(err.message || 'Call failed. Check the number and try again.');
        }
    }

    function handleKeyDown(e) {
        if (e.key === 'Enter') handleCall();
        if (e.key === 'Escape') handleClose();
    }

    const isCalling = status === STATUS.CALLING;

    return (
        <div className="flex flex-col items-end gap-3">
            <AnimatePresence>
                {open && (
                    <motion.div
                        initial={{ opacity: 0, y: 16, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 16, scale: 0.95 }}
                        transition={{ duration: 0.2 }}
                        className="w-72 bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                            <div className="flex items-center gap-2">
                                <Phone className="w-4 h-4 text-primary" />
                                <span className="text-sm font-semibold text-foreground">Outbound Call</span>
                            </div>
                            <button
                                onClick={handleClose}
                                className="text-muted-foreground hover:text-foreground transition-colors"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>

                        {/* Body */}
                        <div className="px-4 py-4 space-y-3">
                            <p className="text-xs text-muted-foreground">
                                Calls the tenant using Alex (the voice agent). The verification
                                and complaint workflow runs exactly like an inbound call.
                            </p>

                            <div className="space-y-1">
                                <label className="text-xs font-medium text-foreground">
                                    Phone Number (E.164)
                                </label>
                                <input
                                    ref={inputRef}
                                    type="tel"
                                    value={number}
                                    onChange={e => {
                                        setNumber(e.target.value);
                                        if (status !== STATUS.IDLE) {
                                            setStatus(STATUS.IDLE);
                                            setErrorMsg('');
                                        }
                                    }}
                                    onKeyDown={handleKeyDown}
                                    disabled={isCalling}
                                    placeholder="+919876543210"
                                    className="w-full bg-background text-foreground text-sm rounded-lg px-3 py-2 border border-border focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50 transition-colors font-mono"
                                />
                            </div>

                            {/* Status messages */}
                            {status === STATUS.ERROR && (
                                <p className="text-xs text-red-500">{errorMsg}</p>
                            )}
                            {status === STATUS.SUCCESS && (
                                <p className="text-xs text-green-500">
                                    Call initiated — Alex is dialling the tenant.
                                </p>
                            )}

                            {/* Call button */}
                            <button
                                onClick={handleCall}
                                disabled={isCalling || !number.trim() || status === STATUS.SUCCESS}
                                className="w-full flex items-center justify-center gap-2 bg-primary text-primary-foreground text-sm font-medium py-2 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-40"
                            >
                                {isCalling ? (
                                    <>
                                        <motion.div
                                            animate={{ rotate: 360 }}
                                            transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                                            className="w-4 h-4 border-2 border-primary-foreground border-t-transparent rounded-full"
                                        />
                                        Calling…
                                    </>
                                ) : status === STATUS.SUCCESS ? (
                                    <>
                                        <PhoneCall className="w-4 h-4" />
                                        Call Placed
                                    </>
                                ) : (
                                    <>
                                        <Phone className="w-4 h-4" />
                                        Call
                                    </>
                                )}
                            </button>

                            {status === STATUS.SUCCESS && (
                                <button
                                    onClick={() => {
                                        setStatus(STATUS.IDLE);
                                        setNumber('+91');
                                    }}
                                    className="w-full text-xs text-muted-foreground hover:text-foreground transition-colors py-1"
                                >
                                    Make another call
                                </button>
                            )}
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* FAB */}
            <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={handleToggle}
                title="Make outbound call"
                className={`w-12 h-12 rounded-full shadow-lg flex items-center justify-center transition-colors ${
                    open
                        ? 'bg-red-500 text-white'
                        : 'bg-secondary text-foreground hover:bg-secondary/80'
                }`}
            >
                {open ? <PhoneOff className="w-5 h-5" /> : <Phone className="w-5 h-5" />}
            </motion.button>
        </div>
    );
}
