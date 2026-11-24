import { useEffect, useState, type FormEvent } from 'react'
import { Link, NavLink, Navigate, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { Activity, Braces, Check, CheckCircle2, ChevronRight, Circle, Code2, FileCode2, FolderGit2, GitBranch, Layers3, LoaderCircle, LockKeyhole, LogOut, Mail, Menu, RefreshCw, ShieldCheck, Terminal, UserRound, X } from 'lucide-react'
import { useAuth } from './auth'
import { supabase } from './supabase'
import { configured } from './config'
import { api, ApiError, type Me, type Project } from './api'

const phases = [
  ['Foundation', 'Authentication, dashboard, API and ownership policies.'],
  ['Project input', 'ZIP uploads, GitHub imports and searchable source files.'],
  ['AI debugging', 'Evidence-based investigation with specialist agents.'],
  ['Results & follow-up', 'Rectification prompts, analysis history and retries.'],
  ['Deployment', 'A tested, hosted workflow within free-tier limits.'],
]
function Brand() { return <Link to="/" className="brand" aria-label="DEBUGGER home"><span className="brand-icon"><Braces size={23} /></span>DEBUGGER<span className="brand-period">.</span></Link> }
function Spinner({ text = 'Restoring your session…' }: { text?: string }) { return <div className="loading-view" role="status"><LoaderCircle className="spin" size={25} /><span>{text}</span></div> }
function Setup() { return <main className="setup"><Brand /><h1>Connect your workspace</h1><p>Set the Supabase URL and publishable key in <code>frontend/.env.local</code>, then restart the development server.</p><p>Use <code>.env.example</code> as a template. Backend secrets never belong in frontend configuration.</p></main> }
function Protected() {
  const { session, loading } = useAuth()
  if (loading) return <Spinner />
  return session ? <Outlet /> : <Navigate to="/login" replace />
}
function AuthPage({ signup = false }: { signup?: boolean }) {
  const { session, loading, error: restoreError } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [sent, setSent] = useState(false)
  useEffect(() => { setError(''); setSent(false); setPassword(''); setConfirm('') }, [signup])
  if (loading) return <Spinner />
  if (session) return <Navigate to="/app" replace />
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!supabase || busy) return
    setError('')
    if (signup && password !== confirm) { setError('Passwords do not match.'); return }
    setBusy(true)
    try {
      const result = signup
        ? await supabase.auth.signUp({ email: email.trim(), password, options: { emailRedirectTo: `${window.location.origin}/auth/callback` } })
        : await supabase.auth.signInWithPassword({ email: email.trim(), password })
      if (result.error) { setError(result.error.message); return }
      setPassword(''); setConfirm('')
      if (signup && !result.data.session) setSent(true)
      else navigate('/app', { replace: true })
    } catch { setError('Unable to reach authentication. Check your connection and retry.') }
    finally { setBusy(false) }
  }
  return <main className="auth-layout">
    <section className="auth-story">
      <Brand />
      <div className="story-content"><span className="eyebrow mint">LESS GUESSWORK. MORE CLARITY.</span><h1>Find the cause.<br /><span>Move forward.</span></h1><p>A focused home for your code, your investigations, and the next step toward a fix.</p>
        <div className="code-window" aria-hidden="true"><div className="code-title"><Terminal size={16} /><span>your next debugging session</span><span className="code-dots">•••</span></div><div className="code-body"><p><span>01</span><b>understand</b>(the_problem)</p><p><span>02</span><b>inspect</b>(the_evidence)</p><p><span>03</span><b>find</b>(the_root_cause)</p><div className="code-result"><CheckCircle2 size={16} /> A clearer path to the fix.</div></div></div>
        <div className="story-proof"><ShieldCheck size={18} /><span>Your projects. Your private workspace.</span></div>
      </div><div className="story-bottom"><span>BUILT FOR THE WAY DEVELOPERS THINK</span><Code2 size={20} /></div>
    </section>
    <section className="auth-panel"><div className="auth-top"><span>Developer workspace</span><span className="version">EARLY ACCESS</span></div>
      <div className="auth-form-wrap">
        {sent ? <div className="confirmation"><div className="form-symbol"><Mail size={26} /></div><h2>Check your inbox</h2><p>If signup is available for <strong>{email}</strong>, a confirmation email is on its way. Open its link, then return here to sign in.</p><p className="muted">Already have an account? Sign in instead. If the message does not arrive, check spam or your project's email delivery settings.</p><Link className="primary button-link" to="/login" onClick={() => setSent(false)}>Back to sign in</Link></div>
        : <><div className="form-symbol"><Terminal size={25} /></div><span className="eyebrow">YOUR NEXT INVESTIGATION STARTS HERE</span><h2>{signup ? 'Create your workspace' : 'Welcome back.'}</h2><p className="form-intro">{signup ? 'A little setup. A lot less guesswork.' : 'Sign in to pick up where you left off.'}</p>
        <form onSubmit={submit}>
          {(error || restoreError || location.state?.expired) && <div className="notice error" role="alert">{error || restoreError || 'Your session expired. Please sign in again.'}</div>}
          <label htmlFor="email">Email address</label><input id="email" type="email" autoComplete="email" placeholder="you@example.com" required maxLength={254} value={email} onChange={e => setEmail(e.target.value)} disabled={busy} />
          <label htmlFor="password">Password</label><input id="password" type="password" autoComplete={signup ? 'new-password' : 'current-password'} placeholder={signup ? 'At least 8 characters' : 'Enter your password'} minLength={signup ? 8 : undefined} maxLength={128} required value={password} onChange={e => setPassword(e.target.value)} disabled={busy} />
          {signup && <><label htmlFor="confirm">Confirm password</label><input id="confirm" type="password" autoComplete="new-password" placeholder="Enter your password again" minLength={8} required value={confirm} onChange={e => setConfirm(e.target.value)} disabled={busy} /></>}
          <button className="primary" type="submit" disabled={busy}>{busy && <LoaderCircle className="spin" size={17} />}{busy ? 'Please wait…' : signup ? 'Create account' : 'Sign in'}</button>
        </form><p className="auth-switch">{signup ? 'Already have an account?' : 'New to DEBUGGER?'} <Link to={signup ? '/login' : '/signup'}>{signup ? 'Sign in' : 'Create an account'}</Link></p><div className="auth-assurance"><LockKeyhole size={15} />Secure email authentication</div></>}
      </div><footer className="auth-footer">A little more context. A better next step.</footer>
    </section>
  </main>
}
function Callback() {
  const { session } = useAuth()
  const [error, setError] = useState('')
  useEffect(() => {
    const query = new URLSearchParams(window.location.search)
    const hash = new URLSearchParams(window.location.hash.slice(1))
    if (query.has('error') || hash.has('error')) setError('This confirmation link is invalid or expired. Return to sign in, or request a new signup confirmation.')
    const timeout = window.setTimeout(() => setError('If your email was confirmed, you can now sign in. Otherwise the link may have expired.'), 8000)
    return () => clearTimeout(timeout)
  }, [])
  if (session) return <Navigate to="/app" replace />
  return <main className="setup"><Brand />{error ? <><h1>Continue to your workspace</h1><p role="status">{error}</p><Link to="/login" className="primary button-link">Sign in</Link></> : <Spinner text="Confirming your email…" />}</main>
}
function Shell() {
  const { session, signOut } = useAuth()
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const location = useLocation()
  useEffect(() => setOpen(false), [location.pathname])
  async function logout() { setBusy(true); setError(''); try { await signOut() } catch { setError('Sign out failed. Please retry.'); } finally { setBusy(false) } }
  return <div className="app-layout">
    <button className="mobile-menu icon-button" aria-label={open ? 'Close navigation' : 'Open navigation'} aria-expanded={open} onClick={() => setOpen(!open)}>{open ? <X /> : <Menu />}</button>
    {open && <button className="nav-scrim" aria-label="Close navigation" onClick={() => setOpen(false)} />}
    <aside className={`sidebar ${open ? 'open' : ''}`}><Brand /><div className="workspace-label">PERSONAL WORKSPACE</div><nav aria-label="Main navigation"><NavLink to="/app" end><FolderGit2 size={19} />Projects</NavLink><NavLink to="/app/roadmap"><Layers3 size={19} />Build progress</NavLink><NavLink to="/app/account"><UserRound size={19} />Account</NavLink></nav>
      <div className="sidebar-note"><div><GitBranch size={17} /><strong>Growing with you</strong></div><p>Your workspace is taking shape. See what's ready and what's next.</p><Link to="/app/roadmap">View build progress <ChevronRight size={15} /></Link></div>
      <div className="user-card"><span className="avatar">{(session?.user.email || 'U')[0].toUpperCase()}</span><div><strong>Personal account</strong><span title={session?.user.email}>{session?.user.email}</span></div></div>
      {error && <p className="sidebar-error" role="alert">{error}</p>}<button className="logout" disabled={busy} onClick={logout}><LogOut size={17} />{busy ? 'Signing out…' : 'Sign out'}</button>
    </aside><div className="workspace"><header className="workspace-header"><span>Workspace <ChevronRight size={14} /> <strong>{location.pathname.endsWith('roadmap') ? 'Build progress' : location.pathname.endsWith('account') ? 'Account' : 'Projects'}</strong></span><span className="version">FOUNDATION / V0.1</span></header><Outlet /><footer className="workspace-footer"><span>DEBUGGER · A clearer path to the fix.</span><span>Personal workspace</span></footer></div>
  </div>
}
function Dashboard() {
  const { session, invalidate } = useAuth()
  const navigate = useNavigate()
  const [projects, setProjects] = useState<Project[]>([])
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const token = session?.access_token
  useEffect(() => {
    if (!token) return
    const controller = new AbortController()
    setLoading(true); setError(''); setProjects([]); setMe(null)
    Promise.all([api<Me>('/me', token, controller.signal), api<Project[]>('/projects', token, controller.signal)])
      .then(([user, rows]) => { if (!controller.signal.aborted) { setMe(user); setProjects(rows) } })
      .catch(err => {
        if (controller.signal.aborted) return
        if (err instanceof ApiError && err.status === 401) { invalidate(); navigate('/login', { replace: true, state: { expired: true } }) }
        else setError(err instanceof Error ? err.message : 'Could not load your workspace.')
      }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
    // invalidate deliberately uses no captured session state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, attempt, navigate])
  return <main className="page-content"><div className="page-heading"><div><span className="eyebrow">YOUR DEBUGGING HOME</span><h1>Projects</h1><p>Give every investigation a place to start.</p></div><span className="phase-chip"><Layers3 size={15} />Phase 1 · Foundation</span></div>
    <section className="welcome-card"><div><span className="eyebrow">FROM ERROR TO UNDERSTANDING</span><h2>Good fixes start<br />with the right context.</h2><p>Bring your code and the problem. Build a clear picture of what went wrong, then take the next step.</p><Link to="/app/roadmap" className="text-link">Explore the build plan <ChevronRight size={16} /></Link></div><div className="context-art" aria-hidden="true"><div className="art-file"><FileCode2 size={27} /><span>source code</span></div><div className="art-connector" /><div className="art-center"><Braces size={34} /></div><div className="art-connector" /><div className="art-file"><CheckCircle2 size={27} /><span>clear next step</span></div></div></section>
    <div className="section-heading"><h2>Your projects {(!loading && !error) && <span className="count">{projects.length}</span>}</h2><button className="quiet-button" disabled={loading} onClick={() => setAttempt(a => a + 1)}><RefreshCw size={15} className={loading ? 'spin' : ''} />Refresh</button></div>
    {loading ? <section className="empty-card"><Spinner text="Connecting to your workspace…" /></section> : error ? <section className="empty-card error-card"><Activity size={32} /><h3>Let's reconnect</h3><p role="alert">{error}</p><button className="secondary" onClick={() => setAttempt(a => a + 1)}>Try again</button></section> : projects.length ? <div className="project-grid">{projects.map(project => <article className="project-card" key={project.id}><FolderGit2 size={24} /><span className="source-label">{project.source_type === 'github' ? 'GitHub' : 'ZIP upload'}</span><h3>{project.name}</h3><p>Created {new Date(project.created_at).toLocaleDateString()}</p><small>Project inspection arrives in Phase 2.</small></article>)}</div> : <section className="empty-card"><div className="empty-icon"><FolderGit2 size={31} /></div><h3>A fresh workspace. A clear start.</h3><p>Your projects will live here. ZIP uploads and GitHub imports<br className="desktop-break" /> are the next step in the build.</p><span className="coming-label">Project imports arrive in Phase 2</span></section>}
    <div className="bottom-grid"><section className="info-card"><ShieldCheck size={22} /><div><h3>Private by design</h3><p>Access policies keep your project records scoped to your account.</p></div></section><section className="info-card"><GitBranch size={22} /><div><h3>One step at a time</h3><p>Imports, investigations, and actionable prompts are coming next.</p></div></section></div>
    <div className="connection-caption"><span className={`connection-dot ${me && !error ? 'connected' : ''}`} />{loading ? 'Checking your connection' : error ? 'Connection needs attention' : 'Authenticated API connection verified'}</div>
  </main>
}
function Roadmap() { return <main className="page-content"><div className="page-heading"><div><span className="eyebrow">BUILT WITH INTENTION</span><h1>Build progress</h1><p>A focused path from foundation to a working debugging workflow.</p></div></div><section className="roadmap-card">{phases.map(([title, description], i) => <div className={`roadmap-row ${i === 0 ? 'current' : ''}`} key={title}><span className="step-icon">{i === 0 ? <Code2 size={22} /> : <Circle size={19} />}</span><div><span className="eyebrow">PHASE {i + 1}</span><h2>{title}</h2><p>{description}</p></div><span className={`status-badge ${i === 0 ? 'active' : ''}`}>{i === 0 ? 'Current phase' : 'Planned'}</span></div>)}</section><p className="roadmap-note">Each phase is verified before it is marked complete. AI analysis and automatic code execution are not enabled in this foundation release.</p></main> }
function Account() { const { session } = useAuth(); return <main className="page-content"><div className="page-heading"><div><span className="eyebrow">YOUR WORKSPACE IDENTITY</span><h1>Account</h1><p>Your sign-in details and workspace access.</p></div></div><section className="account-card"><div className="account-heading"><span className="avatar large"><UserRound size={28} /></span><div><h2>Personal account</h2><p>Email authentication</p></div></div><dl><div><dt>Email address</dt><dd>{session?.user.email}</dd></div><div><dt>Email status</dt><dd>{session?.user.email_confirmed_at ? <span className="verified"><Check size={16} />Confirmed</span> : 'Confirmation pending'}</dd></div><div><dt>Account ID</dt><dd className="mono">{session?.user.id}</dd></div></dl><p className="muted">Use Sign out in the navigation to end this browser's session.</p></section></main> }
function NotFound() { return <main className="setup"><Brand /><span className="eyebrow">404 / NOT FOUND</span><h1>This page took a wrong turn.</h1><p>Let's get you back to your workspace.</p><Link className="primary button-link" to="/app">Back to workspace</Link></main> }
export default function App() {
  if (!configured) return <Setup />
  return <Routes><Route path="/" element={<Navigate to="/app" replace />} /><Route path="/login" element={<AuthPage />} /><Route path="/signup" element={<AuthPage signup />} /><Route path="/auth/callback" element={<Callback />} /><Route element={<Protected />}><Route path="/app" element={<Shell />}><Route index element={<Dashboard />} /><Route path="roadmap" element={<Roadmap />} /><Route path="account" element={<Account />} /></Route></Route><Route path="*" element={<NotFound />} /></Routes>
}
