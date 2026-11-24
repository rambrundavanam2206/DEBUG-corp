import { createClient } from '@supabase/supabase-js'
import { config, configured } from './config'
export const supabase = configured ? createClient(config.url, config.key, {
  auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
}) : null
