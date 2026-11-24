import { useEffect, useState } from 'react'
import { BrainCircuit, LoaderCircle, RefreshCw, FileCode2 } from 'lucide-react'
import { api, mutate } from './api'
import { useAuth } from './auth'

type Evidence = { path: string; start_line: number; end_line: number; quote: string }
type Diagnosis = {
 summary: string; confidence: string; findings: { title: string; explanation: string; suggested_fix: string; evidence: Evidence[] }[];
 suggested_reproduction: string[]; verification_steps: string[]; questions: string[]; limitations: string[];
 rectification_prompt: string; execution_verified: false; evidence_check: string;
}
type Analysis = { id: string; status: string; provider: string; model: string; created_at: string; source_hash: string; stale: boolean; error: string; result: Diagnosis | null; usage: { model_calls?: number; files_read?: number; total_files?: number; specialists?: string[]; fallback_used?: boolean } }
type Config = { ready: boolean; primary: string; configured_providers: string[]; fallback_enabled: boolean; message: string }
const errorText = (e: unknown) => e instanceof Error ? e.message : 'Could not load analysis.'
export function AnalysisPanel({ projectId, ready, revision, onEvidence }: { projectId: string; ready: boolean; revision: string; onEvidence: (path: string, line: number) => void }) {
 const { session } = useAuth()
 const token = session!.access_token
 const base = `/projects/${projectId}/analysis`
 const [config, setConfig] = useState<Config>()
 const [analysis, setAnalysis] = useState<Analysis | null>(null)
 const [busy, setBusy] = useState(false)
 const [loading, setLoading] = useState(true)
 const [error, setError] = useState('')
 const [attempt, setAttempt] = useState(0)
 useEffect(() => {
  const controller = new AbortController(); setLoading(true)
  Promise.all([api<Config>('/ai/config', token, controller.signal), api<{ analysis: Analysis | null }>(base, token, controller.signal)])
   .then(([c, a]) => { if (!controller.signal.aborted) { setConfig(c); setAnalysis(a.analysis) } })
   .catch(e => { if (!controller.signal.aborted) setError(errorText(e)) }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
  return () => controller.abort()
 }, [base, token, revision, attempt])
 const running = busy || analysis?.status === 'running'
 useEffect(() => {
  if (!running || busy) return
  const timer = window.setInterval(() => setAttempt(n => n + 1), 5000)
  return () => clearInterval(timer)
 }, [running, busy])
 async function analyse() {
  if (busy) return
  setBusy(true); setError(''); setAnalysis(null)
  try { const data = await mutate<{ analysis: Analysis }>(base, token, 'POST'); setAnalysis(data.analysis) }
  catch (e) { setError(errorText(e)); setAttempt(n => n + 1) }
  finally { setBusy(false) }
 }
 const result = analysis?.result
 const list = (title: string, items: string[]) => items.length ? <section className="analysis-list"><h3>{title}</h3><ol>{items.map((text, i) => <li key={i}>{text}</li>)}</ol></section> : null
 return <section className="analysis-panel" aria-label="AI investigation"><div className="section-heading"><h2><BrainCircuit size={22} />AI investigation</h2><button className="quiet-button" disabled={busy} onClick={() => setAttempt(n => n + 1)}><RefreshCw size={15} />Refresh analysis</button></div>
  <p className="analysis-intro">Inspect your imported code and saved problem together. Findings include source references and a prompt for your local coding agent.</p>
  <p className="form-hint">Analysis sends selected source and error context to {config?.primary || 'your configured provider'}{config?.fallback_enabled ? ' (with a configured fallback provider)' : ''}. Code is never executed here. Remove secrets before analysing.</p>
  {loading && <p role="status">Checking analysis status…</p>}
  {config && !config.ready && <p className="notice">{config.message}</p>}
  {!ready && <p className="notice">Finish importing your project first.</p>}
  {error && <p role="alert" className="notice error">{error}</p>}
  <button className="primary analyse-button" disabled={loading || !ready || !config?.ready || running} onClick={analyse}>{running ? <><LoaderCircle className="spin" size={17} />Investigating…</> : analysis ? 'Analyze again' : 'Analyze issue'}</button>
  {running && <p role="status" className="form-hint">Reading relevant source and checking evidence. This can take up to two minutes. Refresh restores the saved status; interrupted runs become retryable after three minutes.</p>}
  {analysis && <div className="analysis-meta"><span>{analysis.status.replace('_', ' ')}</span>{analysis.provider && <span>{analysis.provider} · {analysis.model}</span>}<span>{new Date(analysis.created_at).toLocaleString()}</span></div>}
  {analysis?.error && <p role="alert" className="notice error">{analysis.error}</p>}
  {analysis?.stale && <p role="alert" className="notice error">Saved analysis is out of date: source or problem details changed. Analyze again before using these findings.</p>}
  {result && <div className={analysis?.stale ? 'analysis-result stale-result' : 'analysis-result'}><h3>Diagnosis</h3><p>{result.summary}</p><p className="form-hint">AI confidence: {result.confidence}. This is a source-based assessment, not a verified fix.</p>
   {result.findings.map((finding, i) => <article className="finding-card" key={i}><h3>{finding.title}</h3><p>{finding.explanation}</p><p><strong>Suggested change:</strong> {finding.suggested_fix}</p>{finding.evidence.map((e, j) => <div key={j} className="evidence"><button className="text-link" onClick={() => onEvidence(e.path, e.start_line)}><FileCode2 size={15} />{e.path}:{e.start_line}–{e.end_line}</button><pre>{e.quote}</pre></div>)}</article>)}
   {list('Suggested reproduction — not executed', result.suggested_reproduction)}{list('Verification steps — not executed', result.verification_steps)}{list('More context needed', result.questions)}{list('Limitations', result.limitations)}
   <p className="form-hint">{result.evidence_check}</p>
   {result.rectification_prompt && <div><label htmlFor="rectification">Rectification prompt</label><p className="form-hint">Paste into your local coding agent. It must verify current code before applying changes.</p><textarea id="rectification" className="rectification-text" readOnly value={result.rectification_prompt} rows={14} /></div>}
   <p className="form-hint">Inspected {analysis?.usage.files_read ?? 0} of {analysis?.usage.total_files ?? 0} files · {analysis?.usage.model_calls ?? 0} model calls{analysis?.usage.specialists?.length ? ` · Specialists: ${analysis.usage.specialists.join(', ')}` : ''}{analysis?.usage.fallback_used ? ' · Fallback provider used' : ''}</p>
  </div>}
 </section>
}
