import { config } from './config'
export class ApiError extends Error { constructor(message: string, public status: number) { super(message) } }
export type Project = { id: string; name: string; source_type: 'zip' | 'github'; status: string; created_at: string; updated_at: string }
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

export async function mutate<T>(path: string, token: string, method: string, body?: unknown): Promise<T> {
  const binary = body instanceof File
  let response: Response
  try {
    response = await fetch(`${config.apiUrl}/api${path}`, {
      method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': binary ? 'application/zip' : 'application/json' },
      body: body === undefined ? undefined : binary ? body : JSON.stringify(body),
      signal: AbortSignal.timeout(150000),
    })
  } catch { throw new ApiError('Connection interrupted. Refresh the project to check its status before retrying.', 0) }
  const data = await response.json()
  if (!response.ok) throw new ApiError(data.error?.message || 'Request failed. Please retry.', response.status)
  return data as T
}
export type Problem = { problem: string; command: string; expected: string; reproduction: string }
export type ProjectDetail = Project & Problem & {
  status: 'pending' | 'importing' | 'ready' | 'failed' | 'deleting'; repo_url: string; branch: string; commit_sha: string;
  import_error: string; manifest: { path: string; size: number; lines: number }[]; skipped: { path: string; reason: string }[];
}
