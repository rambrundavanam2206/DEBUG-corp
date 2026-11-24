import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, FileCode2, GitBranch, Upload, LoaderCircle, Search, Trash2 } from 'lucide-react'
import { useAuth } from './auth'
import { api, mutate, type ProjectDetail, type Problem } from './api'

const emptyProblem: Problem = { problem: '', command: '', expected: '', reproduction: '' }
const message = (e: unknown) => e instanceof Error ? e.message : 'Something went wrong. Please retry.'
function ProblemFields({ value, change }: { value: Problem; change: (value: Problem) => void }) {
  const field = (key: keyof Problem, label: string, max: number, required = false) => <div><label htmlFor={key}>{label}</label><textarea id={key} value={value[key]} onChange={e => change({ ...value, [key]: e.target.value })} maxLength={max} required={required} rows={key === 'problem' ? 8 : 2} placeholder={key === 'problem' ? 'Paste the terminal error and stack trace, or describe what went wrong…' : 'Optional'} /></div>
  return <>{field('problem', 'Terminal error / problem description', 30000, true)}<details className="extra-details"><summary>Additional context (optional)</summary>{field('command', 'Command you ran', 1000)}{field('expected', 'Expected behaviour', 5000)}{field('reproduction', 'Reproduction steps', 5000)}</details></>
}
export function NewProject() {
  const { session } = useAuth()
  const navigate = useNavigate()
  const [source, setSource] = useState<'github' | 'zip'>('github')
  const [name, setName] = useState('')
  const [repo, setRepo] = useState('')
  const [branch, setBranch] = useState('')
  const [file, setFile] = useState<File>()
  const [problem, setProblem] = useState(emptyProblem)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(e: FormEvent) {
    e.preventDefault()
    if (busy || !session) return
    if (source === 'zip' && (!file || file.size > 10 * 1024 * 1024)) { setError('Choose a ZIP file of up to 10 MB.'); return }
    if (!name.trim() || !problem.problem.trim()) { setError('Project name and problem description are required.'); return }
    setBusy(true); setError('')
    try {
      const project = await mutate<ProjectDetail>('/projects', session.access_token, 'POST', { name, source_type: source, repo_url: source === 'github' ? repo : '', branch, ...problem })
      // Navigate immediately: a failed import keeps the project ID and a recoverable retry screen.
      navigate(`/app/projects/${project.id}`, { state: { file, startImport: true } })
    } catch (e) { setError(message(e)); setBusy(false) }
  }
  return <main className="page-content"><Link className="back-link" to="/app"><ArrowLeft size={16} />Projects</Link><div className="page-heading"><div><span className="eyebrow">START WITH THE CONTEXT</span><h1>New project</h1><p>Bring your source code and the error you want to understand.</p></div></div>
    <form onSubmit={submit} className="project-form"><fieldset disabled={busy}><label htmlFor="project-name">Project name</label><input id="project-name" value={name} onChange={e => setName(e.target.value)} maxLength={120} required placeholder="e.g. Tic Tac Toe" />
      <div className="source-tabs" role="group" aria-label="Project source"><button type="button" aria-pressed={source === 'github'} onClick={() => setSource('github')}><GitBranch size={18} />Public GitHub repository</button><button type="button" aria-pressed={source === 'zip'} onClick={() => setSource('zip')}><Upload size={18} />Upload ZIP</button></div>
      {source === 'github' ? <><label htmlFor="repo">GitHub repository URL</label><input id="repo" type="url" required value={repo} onChange={e => setRepo(e.target.value)} placeholder="https://github.com/owner/repository" maxLength={300} /><label htmlFor="branch">Branch (optional)</label><input id="branch" value={branch} onChange={e => setBranch(e.target.value)} placeholder="Default branch" maxLength={200} /></> : <div className="upload-box"><Upload size={28} /><label htmlFor="archive">Project ZIP · up to 10 MB</label><input id="archive" type="file" accept=".zip,application/zip" required onChange={e => setFile(e.target.files?.[0])} /><p>Up to 500 source files, 30 MB expanded, 500 KB per file.</p></div>}
      <ProblemFields value={problem} change={setProblem} /><p className="form-hint">Remove secrets before importing. Known credential files and generated folders are skipped; filtering cannot detect every secret. Your code is stored privately and is never executed.</p>
      {error && <p role="alert" className="notice error">{error}</p>}<button className="primary" disabled={busy}>{busy ? <><LoaderCircle size={16} className="spin" />Creating project…</> : 'Import project'}</button></fieldset></form>
  </main>
}

import { useLocation } from 'react-router-dom'
type FileView = { path: string; start: number; total_lines: number; lines: string[] }
type SearchResults = { results: { path: string; line: number; text: string }[]; truncated: boolean }
export function ProjectWorkspace() {
  const { projectId } = useParams()
  const { session } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const token = session!.access_token
  const base = `/projects/${projectId}`
  const [project, setProject] = useState<ProjectDetail>()
  const [problem, setProblem] = useState(emptyProblem)
  const [file, setFile] = useState<File | undefined>(location.state?.file)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [view, setView] = useState<FileView>()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResults>()
  const [filter, setFilter] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const autoStarted = useRef(false)
  const requestVersion = useRef(0)
  async function refresh() { const p = await api<ProjectDetail>(base, token); setProject(p); setProblem({ problem: p.problem, command: p.command, expected: p.expected, reproduction: p.reproduction }); return p }
  async function runImport() {
    setBusy(true); setError(''); setNotice('Importing source files…')
    try { const p = await mutate<ProjectDetail>(`${base}/import`, token, 'POST', file); setProject(p); setNotice('Import complete. Source files are ready to inspect.') }
    catch (e) { setError(message(e)); setNotice(''); try { await refresh() } catch { /* keep actionable error */ } }
    finally { setBusy(false) }
  }
  useEffect(() => {
    let active = true
    api<ProjectDetail>(base, token).then(p => { if (!active) return; setProject(p); setProblem({ problem: p.problem, command: p.command, expected: p.expected, reproduction: p.reproduction }); if (location.state?.startImport && !autoStarted.current) { autoStarted.current = true; navigate(location.pathname, { replace: true, state: null }); void runImport() } }).catch(e => { if (active) setError(message(e)) })
    return () => { active = false }
  }, [base, token])
  async function openFile(path: string, start = 1) {
    const version = ++requestVersion.current
    setError(''); setView(undefined)
    try { const data = await api<FileView>(`${base}/file?path=${encodeURIComponent(path)}&start=${start}`, token); if (version === requestVersion.current) setView(data) }
    catch (e) { if (version === requestVersion.current) setError(message(e)) }
  }
  async function save(e: FormEvent) { e.preventDefault(); setBusy(true); setError(''); setNotice(''); try { setProject(await mutate<ProjectDetail>(`${base}/problem`, token, 'PATCH', problem)); setNotice('Problem details saved.') } catch (e) { setError(message(e)) } finally { setBusy(false) } }
  async function search(e: FormEvent) { e.preventDefault(); setError(''); setResults(undefined); try { setResults(await api<SearchResults>(`${base}/search?q=${encodeURIComponent(query)}`, token)) } catch (e) { setError(message(e)) } }
  async function remove() { setBusy(true); setError(''); try { await mutate(base, token, 'DELETE'); navigate('/app') } catch (e) { setError(message(e)); setBusy(false) } }
  return <main className="page-content"><Link className="back-link" to="/app"><ArrowLeft size={16} />Projects</Link>
    {error && <div className="notice error" role="alert">{error}</div>}{notice && <p role="status" className="notice">{notice}</p>}
    {!project ? <><p>Loading project…</p><button className="secondary" onClick={() => refresh().catch(e => setError(message(e)))}>Retry loading</button></> : <>
      <div className="page-heading"><div><span className="eyebrow">PROJECT WORKSPACE</span><h1>{project.name}</h1><p>{project.source_type === 'github' ? `${project.repo_url} · ${project.branch || 'default branch'}` : 'ZIP upload'}</p></div><span className="status-badge active">{busy ? 'Working…' : project.status}</span></div>
      <div className="project-meta"><span>{project.manifest.length} source files</span><span>{project.skipped.length} skipped</span>{project.commit_sha && <code title={project.commit_sha}>Commit {project.commit_sha.slice(0, 12)}</code>}<button className="quiet-button" disabled={busy} onClick={() => refresh().catch(e => setError(message(e)))}>Refresh status</button></div>
      {project.status !== 'ready' && <section className="project-form"><h2>{busy ? 'Import in progress' : 'Finish your import'}</h2><p>{project.import_error || 'Import source files to browse and search your project. Interrupted operations can be retried after three minutes.'}</p>{project.source_type === 'zip' && <><label htmlFor="retry-zip">Select ZIP again to retry</label><input id="retry-zip" type="file" accept=".zip" onChange={e => setFile(e.target.files?.[0])} disabled={busy} /></>}<button className="primary" disabled={busy || (project.source_type === 'zip' && !file)} onClick={runImport}>{busy ? 'Importing…' : 'Import / retry'}</button></section>}
      <section className="project-form"><h2>Problem details</h2><form onSubmit={save}><fieldset disabled={busy}><ProblemFields value={problem} change={setProblem} /><button className="secondary">Save details</button></fieldset></form></section>
      {project.status === 'ready' && <section className="source-section"><div className="section-heading"><h2><FileCode2 size={20} />Source explorer</h2><span className="source-label">Read only</span></div><form className="search-bar" onSubmit={search}><label className="sr-only" htmlFor="source-search">Search source code</label><input id="source-search" value={query} onChange={e => setQuery(e.target.value)} required maxLength={200} placeholder="Search filenames or source text…" /><button className="secondary"><Search size={17} />Search</button></form>
        {results && <div className="search-results"><p>{results.results.length} matches{results.truncated ? ' · showing first 100' : ''}</p>{results.results.map((r, i) => <button key={i} onClick={() => openFile(r.path, r.line)}><strong>{r.path}:{r.line}</strong><span>{r.text}</span></button>)}</div>}
        <div className="source-explorer"><aside className="file-list"><label htmlFor="file-filter">Files</label><input id="file-filter" placeholder="Filter paths…" value={filter} onChange={e => setFilter(e.target.value)} />{project.manifest.filter(f => f.path.toLowerCase().includes(filter.toLowerCase())).map(f => <button key={f.path} className={view?.path === f.path ? 'selected' : ''} onClick={() => openFile(f.path)} title={f.path}><FileCode2 size={15} /><span>{f.path}</span></button>)}</aside><div className="code-panel">{view ? <><div className="code-toolbar"><strong>{view.path}</strong><span>{view.total_lines} lines</span></div><pre>{view.lines.map((line, i) => <div key={i}><span className="line-number">{view.start + i}</span><code>{line || ' '}</code></div>)}</pre><div className="code-paging"><button disabled={view.start <= 1} onClick={() => openFile(view.path, Math.max(1, view.start - 200))}>Previous lines</button><button disabled={view.start + view.lines.length > view.total_lines} onClick={() => openFile(view.path, view.start + 200)}>Next lines</button></div></> : <div className="code-placeholder"><FileCode2 size={30} /><p>Select a file to read its source.</p></div>}</div></div>
      </section>}
      {project.skipped.length > 0 && <details className="project-form"><summary>{project.skipped.length} skipped files</summary><ul className="skip-list">{project.skipped.map(f => <li key={f.path}><code>{f.path}</code> — {f.reason}</li>)}</ul></details>}
      <p className="form-hint">AI diagnosis and rectification prompts arrive in Phase 3. Importing does not run or analyse your code.</p>
      <section className="delete-area">{confirmDelete ? <><p>Delete this project and its stored source files?</p><button className="danger-button" disabled={busy} onClick={remove}>Delete permanently</button><button className="secondary" disabled={busy} onClick={() => setConfirmDelete(false)}>Cancel</button></> : <button className="quiet-button" disabled={busy} onClick={() => setConfirmDelete(true)}><Trash2 size={16} />Delete project</button>}</section>
    </>}
  </main>
}
