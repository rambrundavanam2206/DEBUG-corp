const url = import.meta.env.VITE_SUPABASE_URL?.trim() || ''
const key = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY?.trim() || ''
export const configured = /^https:\/\/[a-z0-9-]+\.supabase\.co$/.test(url) && key.startsWith('sb_publishable_')
export const config = { url, key, apiUrl: (import.meta.env.VITE_API_URL || '').replace(/\/$/, '') }
