import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
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
    const { t } = useTranslation();
    const [open, setOpen] = useState(false);
    const [number, setNumber] = useState('+1');
    const [agentId, setAgentId] = useState('complaint');
    const [status, setStatus] = useState(STATUS.IDLE);
    const [errorMsg, setErrorMsg] = useState('');
    const inputRef = useRef(null);

    const AGENTS = [
        {
            id: 'complaint',
            label: t('outbound.complaintLabel'),
            description: t('outbound.complaintDesc'),
        },
        {
            id: 'lease',
            label: t('outbound.leaseLabel'),
            description: t('outbound.leaseDesc'),
        },
    ];

    useEffect(() => {
        if (open) {
            setTimeout(() => inputRef.current?.focus(), 150);
        }
    }, [open]);

    function handleClose() {
        setOpen(false);
        setStatus(STATUS.IDLE);
        setErrorMsg('');
        setNumber('+1');
        setAgentId('complaint');
    }

    function handleToggle() {
        if (open) handleClose();
        else setOpen(true);
    }

    async function handleCall() {
        const trimmed = number.trim();
        if (!trimmed) return;

        if (!/^\+\d{7,15}$/.test(trimmed)) {
            setStatus(STATUS.ERROR);
            setErrorMsg(t('outbound.invalidNumber'));
            return;
        }

        setStatus(STATUS.CALLING);
        setErrorMsg('');

        try {
            const result = await makeOutboundCall(trimmed, agentId);
            console.log('[Outbound Call]', result);
            setStatus(STATUS.SUCCESS);
        } catch (err) {
            setStatus(STATUS.ERROR);
            setErrorMsg(err.message || t('outbound.failed'));
        }
    }

    function handleKeyDown(e) {
        if (e.key === 'Enter') handleCall();
        if (e.key === 'Escape') handleClose();
    }

    const isCalling = status === STATUS.CALLING;
    const selectedAgent = AGENTS.find(a => a.id === agentId);

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
                                <span className="text-sm font-semibold text-foreground">{t('outbound.title')}</span>
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
                            {/* Agent selector */}
                            <div className="space-y-1">
                                <label className="text-xs font-medium text-foreground">{t('outbound.agent')}</label>
                                <div className="flex rounded-lg border border-border overflow-hidden">
                                    {AGENTS.map(agent => (
                                        <button
                                            key={agent.id}
                                            onClick={() => {
                                                setAgentId(agent.id);
                                                if (status !== STATUS.IDLE) {
                                                    setStatus(STATUS.IDLE);
                                                    setErrorMsg('');
                                                }
                                            }}
                                            disabled={isCalling}
                                            className={`flex-1 text-xs py-1.5 font-medium transition-colors disabled:opacity-50 ${
                                                agentId === agent.id
                                                    ? 'bg-primary text-primary-foreground'
                                                    : 'bg-background text-muted-foreground hover:text-foreground'
                                            }`}
                                        >
                                            {agent.label}
                                        </button>
                                    ))}
                                </div>
                                <p className="text-xs text-muted-foreground">{selectedAgent?.description}</p>
                            </div>

                            {/* Phone number input */}
                            <div className="space-y-1">
                                <label className="text-xs font-medium text-foreground">
                                    {t('outbound.phone')}
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
                                    placeholder="+14165551234"
                                    className="w-full bg-background text-foreground text-sm rounded-lg px-3 py-2 border border-border focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50 transition-colors font-mono"
                                />
                            </div>

                            {/* Status messages */}
                            {status === STATUS.ERROR && (
                                <p className="text-xs text-red-500">{errorMsg}</p>
                            )}
                            {status === STATUS.SUCCESS && (
                                <p className="text-xs text-green-500">
                                    {t('outbound.success', { agent: selectedAgent?.label })}
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
                                        {t('outbound.calling')}
                                    </>
                                ) : status === STATUS.SUCCESS ? (
                                    <>
                                        <PhoneCall className="w-4 h-4" />
                                        {t('outbound.placed')}
                                    </>
                                ) : (
                                    <>
                                        <Phone className="w-4 h-4" />
                                        {t('outbound.call')}
                                    </>
                                )}
                            </button>

                            {status === STATUS.SUCCESS && (
                                <button
                                    onClick={() => {
                                        setStatus(STATUS.IDLE);
                                        setNumber('+1');
                                    }}
                                    className="w-full text-xs text-muted-foreground hover:text-foreground transition-colors py-1"
                                >
                                    {t('outbound.anotherCall')}
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
                title={t('outbound.title')}
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
