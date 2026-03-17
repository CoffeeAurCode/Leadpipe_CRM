import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { MessageCircle, X, Send } from 'lucide-react';
import { sendChatMessage } from '../services/apiService';

export default function Chatbot() {
    const [open, setOpen] = useState(false);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const bottomRef = useRef(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, loading]);

    async function handleSend() {
        const text = input.trim();
        if (!text || loading) return;

        const userMsg = { role: 'user', content: text };
        const updated = [...messages, userMsg];
        setMessages(updated);
        setInput('');
        setLoading(true);

        try {
            const data = await sendChatMessage(updated);
            setMessages(prev => [...prev, { role: 'assistant', content: data.reply }]);
            // Refresh dashboard data in case a tool mutated the DB
            window.dispatchEvent(new Event('refresh-appointments'));
        } catch {
            setMessages(prev => [
                ...prev,
                { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
            ]);
        } finally {
            setLoading(false);
        }
    }

    function handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    }

    return (
        <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end gap-3">
            <AnimatePresence>
                {open && (
                    <motion.div
                        initial={{ opacity: 0, y: 16, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 16, scale: 0.95 }}
                        transition={{ duration: 0.2 }}
                        className="w-[380px] h-[500px] bg-card border border-border rounded-xl shadow-2xl flex flex-col overflow-hidden"
                    >
                        {/* Header */}
                        <div className="flex items-center justify-between px-4 py-3 border-b border-border">
                            <div className="flex items-center gap-2">
                                <div className="w-2 h-2 rounded-full bg-green-500" />
                                <span className="text-sm font-semibold text-foreground">Property Assistant</span>
                            </div>
                            <button
                                onClick={() => setOpen(false)}
                                className="text-muted-foreground hover:text-foreground transition-colors"
                            >
                                <X className="w-4 h-4" />
                            </button>
                        </div>

                        {/* Messages */}
                        <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
                            {messages.length === 0 && (
                                <p className="text-muted-foreground text-sm text-center mt-10">
                                    Ask me about tenants, appointments, or adding units.
                                </p>
                            )}
                            {messages.map((msg, i) => (
                                <div
                                    key={i}
                                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                >
                                    <div
                                        className={`max-w-[85%] px-3 py-2 rounded-xl text-sm whitespace-pre-wrap leading-relaxed ${
                                            msg.role === 'user'
                                                ? 'bg-primary text-primary-foreground rounded-br-sm'
                                                : 'bg-secondary text-foreground rounded-bl-sm'
                                        }`}
                                    >
                                        {msg.content}
                                    </div>
                                </div>
                            ))}
                            {loading && (
                                <div className="flex justify-start">
                                    <div className="bg-secondary text-muted-foreground px-3 py-2 rounded-xl rounded-bl-sm text-sm">
                                        Thinking…
                                    </div>
                                </div>
                            )}
                            <div ref={bottomRef} />
                        </div>

                        {/* Input */}
                        <div className="px-4 py-3 border-t border-border flex gap-2 items-center">
                            <input
                                type="text"
                                value={input}
                                onChange={e => setInput(e.target.value)}
                                onKeyDown={handleKeyDown}
                                disabled={loading}
                                placeholder="Ask something…"
                                className="flex-1 bg-background text-foreground text-sm rounded-lg px-3 py-2 border border-border focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50 transition-colors"
                            />
                            <button
                                onClick={handleSend}
                                disabled={loading || !input.trim()}
                                className="bg-primary text-primary-foreground p-2 rounded-lg hover:opacity-90 transition-opacity disabled:opacity-40"
                            >
                                <Send className="w-4 h-4" />
                            </button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* FAB */}
            <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                onClick={() => setOpen(o => !o)}
                className="w-12 h-12 rounded-full bg-primary text-primary-foreground shadow-lg flex items-center justify-center"
            >
                {open ? <X className="w-5 h-5" /> : <MessageCircle className="w-5 h-5" />}
            </motion.button>
        </div>
    );
}
