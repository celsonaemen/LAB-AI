import { TestBed, fakeAsync, tick, flushMicrotasks } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { Executions, EXECUTION_STREAM, Execution } from './executions';

describe('Executions', () => {
  const snapshot = (state = 'Completed'): Execution => ({ id: 'run-1', task: 'Revisar carteira', workflow: 'portfolio-review', portfolioId: 'balanced', state, agents: [], createdAt: '2026-11-07T12:00:00Z', startedAt: null, finishedAt: null, durationMs: null, result: { summary: 'Concluído' }, error: null, provider: 'deterministic', requireApproval: false });
  let http: HttpTestingController;
  const stream = { addEventListener: jasmine.createSpy(), close: jasmine.createSpy(), onerror: null as (() => void) | null };
  beforeEach(async () => {
    stream.addEventListener.calls.reset(); stream.close.calls.reset();
    await TestBed.configureTestingModule({ imports: [Executions], providers: [provideHttpClient(), provideHttpClientTesting(), { provide: EXECUTION_STREAM, useValue: () => stream }] }).compileComponents();
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());
  it('loads catalog metadata on demand and reports discovery failure', async () => {
    const fixture = TestBed.createComponent(Executions); const app = fixture.componentInstance;
    const pending = app.discoverTools();
    http.expectOne('/api/v1/tools').flush([{ id: 'get_execution_history', description: 'History summaries', inputSchema: { type: 'object' }, allowedAgents: ['report-agent'], requiresApproval: true }]);
    await pending; fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('report-agent');
    expect(fixture.nativeElement.textContent).toContain('Exige aprovação explícita');
    expect(fixture.nativeElement.textContent).toContain('"type": "object"');
    const failed = app.discoverTools(); http.expectOne('/api/v1/tools').flush({}, { status: 504, statusText: 'Timeout' });
    await failed; fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Não foi possível descobrir');
    expect(app.toolsBusy()).toBeFalse();
  });
  it('offers explicit MCP discovery without automatically calling the runtime', () => {
    const fixture = TestBed.createComponent(Executions); fixture.detectChanges();
    http.expectNone('/api/v1/tools');
    expect(fixture.nativeElement.textContent).toContain('Descobrir ferramentas MCP');
  });
  it('explains security blocks while retaining approval controls and masks trace secrets', () => {
    const fixture = TestBed.createComponent(Executions); const app = fixture.componentInstance;
    app.selected.set(snapshot('AwaitingApproval'));
    app.events.set([{ sequence: 1, executionId: 'run-1', type: 'GuardrailBlocked', agentId: 'data-agent', timestamp: '2026-11-07T12:00:00Z', data: { api_key: 'private-value' } }]);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Bloqueado por segurança');
    expect(fixture.nativeElement.textContent).toContain('Aprovar relatório');
    expect(fixture.nativeElement.textContent).not.toContain('private-value');
  });
  it('creates with admitted fields and renders the truthful provider', async () => {
    const fixture = TestBed.createComponent(Executions); const app = fixture.componentInstance;
    app.task = 'Revisar carteira'; app.filter = '{"area":"risco"}';
    const pending = app.create(); const req = http.expectOne('/api/v1/executions');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ task: 'Revisar carteira', workflow: 'portfolio-review', portfolioId: 'balanced', requireApproval: false, metadataFilter: { area: 'risco' } });
    req.flush(snapshot()); await pending;
    http.expectOne('/api/v1/executions/run-1/events?after=0').flush([]);
    await fixture.whenStable(); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Determinístico');
    expect(fixture.nativeElement.textContent).toContain('Concluído');
  });
  it('approves and cancels without a request body', async () => {
    const fixture = TestBed.createComponent(Executions); const app = fixture.componentInstance; app.selected.set(snapshot('AwaitingApproval'));
    const approve = app.action('approve'); const req = http.expectOne('/api/v1/executions/run-1/approve'); expect(req.request.body).toBeNull(); req.flush(snapshot('Running')); await approve;
    http.expectOne('/api/v1/executions/run-1/events?after=0').flush([]);
    const cancel = app.action('cancel'); const stop = http.expectOne('/api/v1/executions/run-1/cancel'); expect(stop.request.body).toBeNull(); stop.flush(snapshot('Cancelled')); await cancel;
    http.expectOne('/api/v1/executions/run-1/events?after=0').flush([{ sequence: 1, executionId: 'run-1', type: 'ExecutionCancelled', agentId: null, timestamp: '2026-11-07T12:00:01Z', data: {} }]);
    await Promise.resolve(); expect(app.events()[0]?.type).toBe('ExecutionCancelled');
    expect(app.selected()?.state).toBe('Cancelled'); fixture.destroy(); expect(stream.close).toHaveBeenCalled();
  });
  it('loads history explicitly and reports HTTP errors', async () => {
    const app = TestBed.createComponent(Executions).componentInstance;
    const pending = app.loadHistory(); http.expectOne('/api/v1/executions?limit=20&offset=0').flush([snapshot()]); await pending; expect(app.history().length).toBe(1);
    app.task = 'Revisar'; const failed = app.create(); http.expectOne('/api/v1/executions').flush({}, { status: 503, statusText: 'Unavailable' }); await failed; expect(app.error()).toContain('Tente novamente'); expect(app.busy()).toBeFalse();
  });
  it('rejects invalid task and metadata before HTTP', async () => {
    const app = TestBed.createComponent(Executions).componentInstance; app.task = 'x'.repeat(501); await app.create(); expect(app.error()).toContain('500');
    app.task = 'Revisar'; app.filter = '[]'; await app.create(); expect(app.error()).toContain('JSON'); http.expectNone('/api/v1/executions');
  });
  it('refreshes snapshots on named execution events and closes at terminal state', fakeAsync(() => {
    const fixture = TestBed.createComponent(Executions); const app = fixture.componentInstance;
    void app.select('run-1'); http.expectOne('/api/v1/executions/run-1').flush(snapshot('Running')); flushMicrotasks();
    http.expectOne('/api/v1/executions/run-1/events?after=0').flush([]); flushMicrotasks();
    expect(stream.addEventListener.calls.mostRecent().args[0]).toBe('execution');
    const event = { sequence: 1, executionId: 'run-1', type: 'completed', agentId: null, timestamp: '2026-11-07T12:00:01Z', data: {} };
    stream.addEventListener.calls.mostRecent().args[1]({ data: JSON.stringify(event) });
    http.expectOne('/api/v1/executions/run-1').flush(snapshot()); flushMicrotasks();
    http.expectOne('/api/v1/executions/run-1/events?after=1').flush([]); flushMicrotasks();
    expect(app.selected()?.state).toBe('Completed'); expect(app.events().length).toBe(1); expect(stream.close).toHaveBeenCalled(); fixture.destroy();
  }));
  it('falls back to polling after stream failure and destroys without cancelling', fakeAsync(() => {
    const fixture = TestBed.createComponent(Executions); const app = fixture.componentInstance;
    void app.select('run-1'); http.expectOne('/api/v1/executions/run-1').flush(snapshot('Running')); flushMicrotasks();
    http.expectOne('/api/v1/executions/run-1/events?after=0').flush([]); flushMicrotasks();
    stream.onerror?.(); tick(3000);
    http.expectOne('/api/v1/executions/run-1').flush(snapshot('Running')); flushMicrotasks();
    http.expectOne('/api/v1/executions/run-1/events?after=0').flush([]); flushMicrotasks();
    expect(app.connection()).toContain('3 segundos'); fixture.destroy(); tick(6000);
    http.expectNone('/api/v1/executions/run-1'); http.expectNone('/api/v1/executions/run-1/cancel');
  }));
  it('does not open a stream when creation completes after leaving the page', async () => {
    const fixture = TestBed.createComponent(Executions); fixture.componentInstance.task = 'Revisar';
    const pending = fixture.componentInstance.create(); const request = http.expectOne('/api/v1/executions'); fixture.destroy();
    request.flush(snapshot('Running')); await pending; expect(stream.addEventListener).not.toHaveBeenCalled();
    http.expectNone('/api/v1/executions/run-1/events?after=0');
  });
  for (const action of ['approve', 'cancel'] as const) {
    it(`ignores a delayed ${action} response after switching executions`, async () => {
      const fixture = TestBed.createComponent(Executions); const app = fixture.componentInstance;
      app.selected.set(snapshot('AwaitingApproval'));
      const pending = app.action(action); const request = http.expectOne(`/api/v1/executions/run-1/${action}`);
      const selection = app.select('run-2'); http.expectOne('/api/v1/executions/run-2').flush({ ...snapshot(), id: 'run-2' }); await selection;
      http.expectOne('/api/v1/executions/run-2/events?after=0').flush([{ sequence: 1, executionId: 'run-2', type: 'ExecutionCompleted', agentId: null, timestamp: '2026-11-07T12:00:01Z', data: {} }]);
      request.flush(snapshot(action === 'cancel' ? 'Cancelled' : 'Running')); await pending;
      expect(app.selected()?.id).toBe('run-2'); expect(app.events().map(event => event.executionId)).toEqual(['run-2']);
      http.expectNone('/api/v1/executions/run-1/events?after=1'); expect(stream.addEventListener).not.toHaveBeenCalled();
    });
  }
  it('refreshes again when approval arrives during an in-flight snapshot', fakeAsync(() => {
    const fixture = TestBed.createComponent(Executions); const app = fixture.componentInstance;
    void app.select('run-1'); http.expectOne('/api/v1/executions/run-1').flush(snapshot('Running')); flushMicrotasks();
    http.expectOne('/api/v1/executions/run-1/events?after=0').flush([]); flushMicrotasks();
    const listener = stream.addEventListener.calls.mostRecent().args[1];
    listener({ data: JSON.stringify({ sequence: 1, executionId: 'run-1', type: 'AgentCompleted' }) });
    const oldSnapshot = http.expectOne('/api/v1/executions/run-1');
    listener({ data: JSON.stringify({ sequence: 2, executionId: 'run-1', type: 'ApprovalRequested' }) });
    oldSnapshot.flush(snapshot('Running')); flushMicrotasks();
    http.expectOne('/api/v1/executions/run-1').flush(snapshot('AwaitingApproval')); flushMicrotasks();
    expect(app.selected()?.state).toBe('AwaitingApproval'); fixture.destroy();
  }));
});
