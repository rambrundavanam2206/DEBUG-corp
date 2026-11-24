// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { NewProject, ProjectWorkspace } from './Projects'
vi.mock('./auth', () => ({ useAuth: () => ({ session: { access_token: 'test-token' } }) }))
vi.mock('./AnalysisPanel', () => ({ AnalysisPanel: () => <div>Analysis panel</div> }))
vi.mock('./config', () => ({ config: { apiUrl: '' } }))
const project = { id: 'p1', name: 'Tic Tac Toe', source_type: 'github', status: 'ready', repo_url: 'https://github.com/test/repo', branch: 'main', commit_sha: 'a'.repeat(40), problem: 'compiler error', command: '', expected: '', reproduction: '', manifest: [{ path: 'TICTAC.CPP', size: 40, lines: 2 }], skipped: [], import_error: '' }
function show(path: string) { return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/new" element={<NewProject />} /><Route path="/app/projects/:projectId" element={<ProjectWorkspace />} /></Routes></MemoryRouter>) }
beforeEach(() => { vi.stubGlobal('fetch', vi.fn()) })
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
function respond(value: unknown, status = 200) { return new Response(JSON.stringify(value), { status }) }
it('creates a GitHub project with optional reproduction empty and starts its import', async () => {
  vi.mocked(fetch).mockImplementation(async (url, options) => {
    if (String(url).endsWith('/import')) return respond(project)
    if (options?.method === 'POST') return respond({ ...project, status: 'pending' }, 201)
    return respond({ ...project, status: 'pending' })
  })
  show('/new'); const user = userEvent.setup()
  await user.type(screen.getByLabelText('Project name'), 'Tic Tac Toe')
  await user.type(screen.getByLabelText('GitHub repository URL'), project.repo_url)
  await user.type(screen.getByLabelText('Terminal error / problem description'), 'compiler error')
  await user.click(screen.getByRole('button', { name: 'Import project' }))
  expect(await screen.findByText('Import complete. Source files are ready to inspect.')).toBeInTheDocument()
  const create = vi.mocked(fetch).mock.calls.find(([url]) => String(url) === '/api/projects')!
  expect(JSON.parse(create[1]!.body as string).reproduction).toBe('')
  expect(vi.mocked(fetch).mock.calls.filter(([url]) => String(url).endsWith('/import'))).toHaveLength(1)
})
it('shows project quota errors without navigating away', async () => {
  vi.mocked(fetch).mockResolvedValue(respond({ error: { message: 'You can keep up to 3 projects.' } }, 409))
  show('/new'); const user = userEvent.setup()
  await user.type(screen.getByLabelText('Project name'), 'Test')
  await user.type(screen.getByLabelText('GitHub repository URL'), project.repo_url)
  await user.type(screen.getByLabelText('Terminal error / problem description'), 'Error')
  await user.click(screen.getByRole('button', { name: 'Import project' }))
  expect(await screen.findByRole('alert')).toHaveTextContent('3 projects')
})
it('opens source as text and navigates search results to matching lines', async () => {
  vi.mocked(fetch).mockImplementation(async url => {
    if (String(url).includes('/search?')) return respond({ results: [{ path: 'TICTAC.CPP', line: 2, text: 'cout >>' }], truncated: false })
    if (String(url).includes('/file?')) return respond({ path: 'TICTAC.CPP', start: 2, total_lines: 2, lines: ['<script>not executed</script>'] })
    return respond(project)
  })
  show('/app/projects/p1'); const user = userEvent.setup()
  await screen.findByRole('heading', { name: 'Tic Tac Toe' })
  await user.type(screen.getByLabelText('Search source code'), 'cout')
  await user.click(screen.getByRole('button', { name: /^Search$/ }))
  await user.click(await screen.findByRole('button', { name: /TICTAC.CPP:2/ }))
  expect(await screen.findByText('<script>not executed</script>')).toBeInTheDocument()
  expect(document.querySelector('.code-panel script')).toBeNull()
})
it('saves problem details and requires explicit delete confirmation', async () => {
  vi.mocked(fetch).mockImplementation(async (_, options) => respond(options?.method === 'PATCH' ? { ...project, problem: 'new error' } : project))
  show('/app/projects/p1'); const user = userEvent.setup()
  await screen.findByRole('heading', { name: 'Tic Tac Toe' })
  await user.clear(screen.getByLabelText('Terminal error / problem description'))
  await user.type(screen.getByLabelText('Terminal error / problem description'), 'new error')
  await user.click(screen.getByRole('button', { name: 'Save details' }))
  expect(await screen.findByText('Problem details saved.')).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: 'Delete project' }))
  expect(screen.getByRole('button', { name: 'Delete permanently' })).toBeInTheDocument()
  expect(vi.mocked(fetch).mock.calls.some(([, o]) => o?.method === 'DELETE')).toBe(false)
})
it('failed ZIP retry asks for file before analysis', async () => {
  vi.mocked(fetch).mockResolvedValue(respond({ ...project, source_type: 'zip', status: 'failed', import_error: 'Invalid ZIP', manifest: [] }))
  show('/app/projects/p1')
  await waitFor(() => expect(screen.getByRole('button', { name: 'Import / retry' })).toBeDisabled())
  expect(screen.getByLabelText('Select ZIP again to retry')).toBeInTheDocument()
  expect(screen.getByText('Analysis panel')).toBeInTheDocument()
})
