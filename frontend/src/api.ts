import { config } from './config'
export class ApiError extends Error { constructor(message: string, public status: number) { super(message) } }
export type Project = { id: string; name: string; source_type: 'zip' | 'github'; created_at: string; updated_at: string }
export type Me = { id: string; email: string | null }
export async function api<T>(path: string, token: string, signal?: AbortSignal): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${config.apiUrl}/api${path}`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(15000)]) : AbortSignal.timeout(15000),
    })
  } catch (error) {
    if (signal?.aborted) throw error
    throw new ApiError('The backend is unavailable or taking too long. Please retry.', 0)
  }
  let body
  try { body = await response.json() } catch { throw new ApiError('The server returned an unexpected response. Please retry.', response.status) }
  if (!response.ok) throw new ApiError(body.error?.message || 'Something went wrong. Please retry.', response.status)
  return body as T
}
