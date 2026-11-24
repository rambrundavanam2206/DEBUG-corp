// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AnalysisPanel } from './AnalysisPanel'
vi.mock('./auth', () => ({ useAuth: () => ({ session: { access_token: 'test-token' } }) }))
vi.mock('./config', () => ({ config: { apiUrl: '' } }))
const config={ ready:true,primary:'gemini',configured_providers:['gemini'],fallback_enabled:false,message:'Ready' }
const result={ summary:'Missing semicolon',confidence:'high',findings:[{ title:'Missing semicolon', explanation:'Namespace declaration lacks a terminator.',suggested_fix:'Add a semicolon.',evidence:[{path:'TICTAC.CPP',start_line:2,end_line:2,quote:'using namespace std'}]}],suggested_reproduction:['Compile locally'],verification_steps:['Recompile'],questions:[],limitations:['Not executed'],rectification_prompt:'Verify current code before changing it.',execution_verified:false,evidence_check:'References match inspected snapshot.' }
const analysis={id:'a',status:'completed',provider:'gemini',model:'test-model',created_at:'2026-11-24T00:00:00Z',stale:false,error:'',result,usage:{model_calls:2,files_read:1,total_files:1,specialists:[]}}
function response(data: unknown) { return new Response(JSON.stringify(data),{status:200}) }
beforeEach(()=>vi.stubGlobal('fetch',vi.fn()))
afterEach(()=>{cleanup();vi.unstubAllGlobals()})
it('disables analysis and explains missing backend configuration',async()=>{
 vi.mocked(fetch).mockImplementation(async url=>response(String(url).endsWith('/config')?{...config,ready:false,message:'Set provider key and model in backend/.env'}:{analysis:null}))
 render(<AnalysisPanel projectId="p" ready revision="1" onEvidence={()=>{}} />)
 expect(await screen.findByText('Set provider key and model in backend/.env')).toBeInTheDocument()
 expect(screen.getByRole('button',{name:'Analyze issue'})).toBeDisabled()
})
it('runs analysis, renders evidence and opens the actual source line',async()=>{
 vi.mocked(fetch).mockImplementation(async (url,options)=>response(String(url).endsWith('/config')?config:{analysis:options?.method==='POST'?analysis:null}))
 const onEvidence=vi.fn();render(<AnalysisPanel projectId="p" ready revision="1" onEvidence={onEvidence} />)
 const user=userEvent.setup();await waitFor(()=>expect(screen.getByRole('button',{name:'Analyze issue'})).toBeEnabled())
 await user.click(screen.getByRole('button',{name:'Analyze issue'}))
 expect(await screen.findByLabelText('Rectification prompt')).toHaveValue('Verify current code before changing it.')
 await user.click(screen.getByRole('button',{name:'TICTAC.CPP:2–2'}));expect(onEvidence).toHaveBeenCalledWith('TICTAC.CPP',2)
 expect(screen.getByText(/not a verified fix/)).toBeInTheDocument()
})
it('restores stale result with a prominent warning',async()=>{
 vi.mocked(fetch).mockImplementation(async url=>response(String(url).endsWith('/config')?config:{analysis:{...analysis,stale:true}}))
 render(<AnalysisPanel projectId="p" ready revision="2" onEvidence={()=>{}} />)
 expect(await screen.findByRole('alert')).toHaveTextContent('out of date')
 expect(screen.getByRole('button',{name:'Analyze again'})).toBeEnabled()
})
it('shows quota failures with retry and no fabricated result',async()=>{
 vi.mocked(fetch).mockImplementation(async url=>response(String(url).endsWith('/config')?config:{analysis:{...analysis,status:'failed',result:null,error:'Provider quota reached. Retry later.'}}))
 render(<AnalysisPanel projectId="p" ready revision="1" onEvidence={()=>{}} />)
 expect(await screen.findByRole('alert')).toHaveTextContent('quota reached')
 expect(screen.queryByLabelText('Rectification prompt')).not.toBeInTheDocument()
 expect(screen.getByRole('button',{name:'Analyze again'})).toBeEnabled()
})
it('needs-context result asks questions without offering a fix',async()=>{
 vi.mocked(fetch).mockImplementation(async url=>response(String(url).endsWith('/config')?config:{analysis:{...analysis,status:'needs_context',result:{...result,findings:[],questions:['Which command fails?'],rectification_prompt:''}}}))
 render(<AnalysisPanel projectId="p" ready revision="1" onEvidence={()=>{}} />)
 expect(await screen.findByText('Which command fails?')).toBeInTheDocument()
 expect(screen.queryByLabelText('Rectification prompt')).not.toBeInTheDocument()
})
