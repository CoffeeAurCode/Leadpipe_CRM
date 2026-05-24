import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { supabase } from '../lib/supabase';
import Logo from './icon.svg';

export default function AuthPage() {
    const { t } = useTranslation();
    const [mode, setMode] = useState('login'); // 'login' | 'signup'
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [phone, setPhone] = useState('');
    const [loading, setLoading] = useState(false);
    const [googleLoading, setGoogleLoading] = useState(false);
    const [error, setError] = useState(null);
    const [message, setMessage] = useState(null);

    const handleEmailAuth = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setMessage(null);

        try {
            if (mode === 'signup') {
                if (!name) { setError(t('auth.nameRequired')); setLoading(false); return; }

                const { data, error: signUpError } = await supabase.auth.signUp({
                    email,
                    password,
                });

                if (signUpError) { setError(signUpError.message); setLoading(false); return; }

                if (data.user) {
                    const { error: profileError } = await supabase
                        .from('manager_profiles')
                        .insert({
                            user_id: data.user.id,
                            name,
                            phone: phone || null,
                        });

                    if (profileError) {
                        console.error('Profile creation error:', profileError);
                    }
                }

                setMessage(t('auth.accountCreated'));
            } else {
                const { error: signInError } = await supabase.auth.signInWithPassword({
                    email,
                    password,
                });

                if (signInError) { setError(signInError.message); setLoading(false); return; }
            }
        } catch {
            setError(t('auth.unexpectedError'));
            setLoading(false);
        }
    };

    const handleGoogleAuth = async () => {
        setError(null);
        setGoogleLoading(true);
        const { error } = await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: window.location.origin,
            },
        });
        if (error) {
            setError(error.message);
            setGoogleLoading(false);
        }
    };

    return (
        <div className="flex items-center justify-center min-h-screen bg-background">
            <div className="w-full max-w-sm mx-auto px-6">
                {/* Logo */}
                <div className="flex flex-col items-center mb-8">
                    <img src={Logo} alt="LeadPipe" className="w-14 h-14 mb-3" />
                    <h1 className="text-2xl font-semibold text-foreground">
                        {mode === 'login' ? t('auth.signIn') : t('auth.createAccount')}
                    </h1>
                    <p className="text-sm text-muted-foreground mt-1">
                        {mode === 'login' ? t('auth.signInSubtitle') : t('auth.createSubtitle')}
                    </p>
                </div>

                {/* Google Button */}
                <button
                    onClick={handleGoogleAuth}
                    disabled={googleLoading}
                    className="w-full flex items-center justify-center gap-3 px-4 py-3 rounded-lg border border-border bg-card text-foreground hover:bg-secondary transition-colors mb-6 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {googleLoading ? (
                        <div className="w-5 h-5 rounded-full border-2 border-muted-foreground border-t-transparent animate-spin" />
                    ) : (
                        <svg className="w-5 h-5" viewBox="0 0 24 24">
                            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                        </svg>
                    )}
                    {googleLoading ? t('auth.connectingGoogle') : t('auth.continueGoogle')}
                </button>

                {/* Divider */}
                <div className="relative mb-6">
                    <div className="absolute inset-0 flex items-center">
                        <div className="w-full border-t border-border" />
                    </div>
                    <div className="relative flex justify-center text-xs">
                        <span className="bg-background px-2 text-muted-foreground uppercase">{t('auth.or')}</span>
                    </div>
                </div>

                {/* Email Form */}
                <form onSubmit={handleEmailAuth} className="space-y-4">
                    {mode === 'signup' && (
                        <>
                            <div>
                                <label className="block text-sm font-medium text-foreground mb-1.5">{t('auth.fullName')}</label>
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    placeholder="John Doe"
                                    className="w-full px-3 py-2.5 rounded-lg border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                                    required
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-foreground mb-1.5">{t('auth.phone')}</label>
                                <input
                                    type="tel"
                                    value={phone}
                                    onChange={(e) => setPhone(e.target.value)}
                                    placeholder="+1 (555) 000-0000"
                                    className="w-full px-3 py-2.5 rounded-lg border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                                />
                            </div>
                        </>
                    )}

                    <div>
                        <label className="block text-sm font-medium text-foreground mb-1.5">{t('auth.email')}</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="name@example.com"
                            className="w-full px-3 py-2.5 rounded-lg border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                            required
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-foreground mb-1.5">{t('auth.password')}</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="••••••••"
                            className="w-full px-3 py-2.5 rounded-lg border border-border bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary"
                            required
                            minLength={6}
                        />
                    </div>

                    {error && (
                        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                            {error}
                        </div>
                    )}

                    {message && (
                        <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/30 text-green-400 text-sm">
                            {message}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full px-4 py-2.5 rounded-lg bg-primary text-primary-foreground font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        {loading
                            ? (mode === 'login' ? t('auth.signingIn') : t('auth.creating'))
                            : (mode === 'login' ? t('auth.signInBtn') : t('auth.createBtn'))
                        }
                    </button>
                </form>

                {/* Toggle */}
                <p className="text-center text-sm text-muted-foreground mt-6">
                    {mode === 'login' ? t('auth.noAccount') + ' ' : t('auth.haveAccount') + ' '}
                    <button
                        onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(null); setMessage(null); }}
                        className="text-primary hover:underline font-medium"
                    >
                        {mode === 'login' ? t('auth.signUp') : t('auth.signInBtn')}
                    </button>
                </p>
            </div>
        </div>
    );
}
