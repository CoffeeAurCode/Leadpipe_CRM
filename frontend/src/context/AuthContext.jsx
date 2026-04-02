import { createContext, useContext, useState, useEffect, useRef } from 'react';
import { supabase } from '../lib/supabase';

const AuthContext = createContext(null);

/**
 * Ensures a manager_profiles row exists for this user.
 * Needed for Google OAuth users who bypass the signup form.
 */
async function ensureManagerProfile(user) {
    try {
        const { data } = await supabase
            .from('manager_profiles')
            .select('id')
            .eq('user_id', user.id)
            .maybeSingle();

        if (!data) {
            await supabase.from('manager_profiles').insert({
                user_id: user.id,
                name: user.user_metadata?.full_name || user.email?.split('@')[0] || 'Manager',
                phone: user.user_metadata?.phone || null,
            });
        }
    } catch (err) {
        console.error('Failed to ensure manager profile:', err);
    }
}

export function AuthProvider({ children }) {
    const [session, setSession] = useState(null);
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const profileChecked = useRef(false);

    useEffect(() => {
        // onAuthStateChange fires for INITIAL_SESSION (including URL hash detection),
        // SIGNED_IN, TOKEN_REFRESHED, and SIGNED_OUT — making it the single source of truth.
        const { data: { subscription } } = supabase.auth.onAuthStateChange(
            (event, session) => {
                setSession(session);
                setUser(session?.user ?? null);

                // Ensure manager profile exists on first sign-in (e.g. Google OAuth)
                if (session?.user && !profileChecked.current) {
                    profileChecked.current = true;
                    ensureManagerProfile(session.user);
                }
                if (!session) {
                    profileChecked.current = false;
                }

                // INITIAL_SESSION fires once when the client finishes initialization
                // (including URL hash detection). Only then is it safe to stop loading.
                if (event === 'INITIAL_SESSION') {
                    setLoading(false);
                }
            }
        );

        return () => subscription.unsubscribe();
    }, []);

    const signOut = async () => {
        await supabase.auth.signOut();
        // Redirect handled by onAuthStateChange → AuthGate
    };

    return (
        <AuthContext.Provider value={{ session, user, loading, signOut }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
