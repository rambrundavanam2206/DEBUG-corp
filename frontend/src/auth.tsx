import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from './supabase'

type AuthState = { session: Session | null; loading: boolean; error: string; signOut: () => Promise<void>; invalidate: () => void }
const AuthContext = createContext<AuthState | null>(null)
export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!supabase) { setLoading(false); return }
    let alive = true
    let authChanged = false
    const { data } = supabase.auth.onAuthStateChange((_event, next) => {
      authChanged = true
      if (alive) { setSession(next); setLoading(false) }
    })
    supabase.auth.getSession().then(({ data, error }) => {
      if (!alive || authChanged) return
      setSession(data.session)
      if (error) setError('Could not restore your session. Please sign in again.')
      setLoading(false)
    }).catch(() => {
      if (alive && !authChanged) { setError('Could not restore your session. Please sign in again.'); setLoading(false) }
    })
    return () => { alive = false; data.subscription.unsubscribe() }
  }, [])
  async function signOut() {
    const result = await supabase?.auth.signOut({ scope: 'local' })
    if (result?.error) throw new Error('Could not sign out. Please retry.')
    setSession(null)
  }
  function invalidate() {
    setSession(null)
    void supabase?.auth.signOut({ scope: 'local' }).catch(() => {})
  }
  return <AuthContext.Provider value={{ session, loading, error, signOut, invalidate }}>{children}</AuthContext.Provider>
}
export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('AuthProvider is required')
  return value
}
