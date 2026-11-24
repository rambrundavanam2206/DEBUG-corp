// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
const auth = vi.hoisted(() => ({ session: null as any, loading: false, error: '', signOut: vi.fn(), invalidate: vi.fn() }))
const signup = vi.hoisted(() => vi.fn())
const signin = vi.hoisted(() => vi.fn())
vi.mock('./auth', () => ({ useAuth: () => auth }))
vi.mock('./config', () => ({ configured: true, config: { apiUrl: '' } }))
vi.mock('./supabase', () => ({ supabase: { auth: { signUp: signup, signInWithPassword: signin } } }))
function show(path: string) { return render(<MemoryRouter initialEntries={[path]}><App /></MemoryRouter>) }
beforeEach(() => { auth.session = null; auth.loading = false; auth.invalidate.mockReset(); vi.stubGlobal('fetch', vi.fn()); signup.mockReset(); signin.mockReset() })
afterEach(() => { cleanup(); vi.unstubAllGlobals() })
describe('auth and protected workspace', () => {
  it('redirects unauthenticated dashboard access to sign in', async () => {
    show('/app'); expect(await screen.findByRole('heading', { name: 'Welcome back.' })).toBeInTheDocument()
  })
  it('does not render private pages during session restoration', () => {
    auth.loading = true; show('/app'); expect(screen.getByRole('status')).toHaveTextContent('Restoring your session'); expect(screen.queryByRole('heading', { name: 'Projects' })).not.toBeInTheDocument()
  })
  it('rejects mismatched signup passwords before calling provider', async () => {
    show('/signup'); const user = userEvent.setup()
    await user.type(screen.getByLabelText('Email address'), 'test@example.com')
    await user.type(screen.getByLabelText('Password', { exact: true }), 'secure-password')
    await user.type(screen.getByLabelText('Confirm password'), 'another-password')
    await user.click(screen.getByRole('button', { name: 'Create account' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Passwords do not match'); expect(signup).not.toHaveBeenCalled()
  })
  it('shows email confirmation after signup without session', async () => {
    signup.mockResolvedValue({ data: { session: null }, error: null }); show('/signup'); const user = userEvent.setup()
    await user.type(screen.getByLabelText('Email address'), 'test@example.com')
    await user.type(screen.getByLabelText('Password', { exact: true }), 'secure-password')
    await user.type(screen.getByLabelText('Confirm password'), 'secure-password')
    await user.click(screen.getByRole('button', { name: 'Create account' }))
    expect(await screen.findByRole('heading', { name: 'Check your inbox' })).toBeInTheDocument()
  })
  it('shows provider login errors', async () => {
    signin.mockResolvedValue({ error: { message: 'Invalid login credentials' } }); show('/login'); const user = userEvent.setup()
    await user.type(screen.getByLabelText('Email address'), 'test@example.com'); await user.type(screen.getByLabelText('Password'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' })); expect(await screen.findByRole('alert')).toHaveTextContent('Invalid login credentials')
  })
  it('shows genuine empty projects after successful authenticated requests', async () => {
    auth.session = { access_token: 'test-token', user: { email: 'test@example.com' } }
    vi.mocked(fetch).mockImplementation(async (input) => new Response(JSON.stringify(String(input).endsWith('/me') ? { id: 'a', email: 'test@example.com' } : []), { status: 200 }))
    show('/app'); expect(await screen.findByText('A fresh workspace. A clear start.')).toBeInTheDocument()
    expect(screen.getByText('Authenticated API connection verified')).toBeInTheDocument()
    expect(vi.mocked(fetch).mock.calls[0][1]?.headers).toEqual({ Authorization: 'Bearer test-token' })
  })
  it('shows retry UI when backend is offline', async () => {
    auth.session = { access_token: 'test-token', user: { email: 'test@example.com' } }; vi.mocked(fetch).mockRejectedValue(new TypeError('Failed to fetch'))
    show('/app'); expect(await screen.findByRole('alert')).toHaveTextContent('backend is unavailable'); expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument()
  })
  it('invalidates an expired session rather than showing private data', async () => {
    auth.session = { access_token: 'old-token', user: { email: 'test@example.com' } }
    auth.invalidate.mockImplementation(() => { auth.session = null })
    vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ error: { message: 'Expired' } }), { status: 401 }))
    show('/app'); await waitFor(() => expect(auth.invalidate).toHaveBeenCalled())
    expect(await screen.findByRole('heading', { name: 'Welcome back.' })).toBeInTheDocument()
  })
})
