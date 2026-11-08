import { Component, InjectionToken, OnDestroy, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { DatePipe, JsonPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';

export interface Execution {
  id: string; task: string; workflow: string; portfolioId: string; state: string;
  agents: { id: string; state: string; startedAt: string | null; finishedAt: string | null; durationMs: number | null; result: unknown; error: string | null }[];
  createdAt: string; startedAt: string | null; finishedAt: string | null; durationMs: number | null;
  result: unknown; error: string | null; provider: string; requireApproval: boolean;
}
interface ToolDescriptor { id: string; description: string; inputSchema: Record<string, unknown>; allowedAgents: string[]; requiresApproval: boolean; }
interface ExecutionEvent { sequence: number; executionId: string; type: string; agentId: string | null; timestamp: string; data: unknown; }
interface Stream { addEventListener(type: string, listener: (event: MessageEvent<string>) => void): void; close(): void; onerror: ((event: Event) => void) | null; }
export const EXECUTION_STREAM = new InjectionToken<(url: string) => Stream>('execution stream', { providedIn: 'root', factory: () => url => new EventSource(url) });

@Component({ selector: 'app-executions', imports: [FormsModule, JsonPipe, DatePipe], templateUrl: './executions.html', styleUrls: ['./app.css', './executions.css'] })
export class Executions implements OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly openStream = inject(EXECUTION_STREAM);
  private stream: Stream | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private generation = 0;
  private destroyed = false;
  private refreshingGeneration: number | null = null;
  private refreshQueued = false;
  task = ''; workflow = 'portfolio-review'; portfolioId = 'balanced'; requireApproval = false; filter = '{}';
  readonly selected = signal<Execution | null>(null);
  readonly history = signal<Execution[]>([]);
  readonly events = signal<ExecutionEvent[]>([]);
  readonly busy = signal(false); readonly historyBusy = signal(false); readonly historyLoaded = signal(false);
  readonly error = signal(''); readonly connection = signal('');
  readonly tools = signal<ToolDescriptor[]>([]);
  readonly toolsBusy = signal(false); readonly toolsLoaded = signal(false); readonly toolsError = signal('');
  async discoverTools(): Promise<void> {
    if (this.toolsBusy()) return;
    this.toolsBusy.set(true); this.toolsError.set('');
    try {
      const tools = await firstValueFrom(this.http.get<ToolDescriptor[]>('/api/v1/tools'));
      if (!this.destroyed) { this.tools.set(tools); this.toolsLoaded.set(true); }
    } catch { if (!this.destroyed) this.toolsError.set('Não foi possível descobrir ferramentas MCP. Tente novamente.'); }
    finally { this.toolsBusy.set(false); }
  }
  eventLabel(type: string): string {
    return ({ McpDiscovered: 'Ferramentas MCP descobertas', ToolCallRequested: 'Chamada de ferramenta solicitada', McpToolStarted: 'Ferramenta MCP iniciada', McpToolCompleted: 'Ferramenta MCP concluída', GuardrailBlocked: 'Bloqueado por segurança', ModelStarted: 'Inferência iniciada', ModelCompleted: 'Inferência concluída', ModelFailed: 'Falha de inferência', ModelRequested: 'Solicitação ao modelo', ModelResponse: 'Resposta do modelo' } as Record<string, string>)[type] ?? type;
  }
  // Additional display masking only; runtime authorization and redaction remain authoritative.
  safeDisplay(value: unknown): unknown {
    if (typeof value === 'string') return value.replace(/\bBearer\s+[^\s"',;]+/gi, 'Bearer [REDACTED]').replace(/\bsk-[a-zA-Z0-9_-]{8,}/g, '[REDACTED]');
    if (Array.isArray(value)) return value.map(item => this.safeDisplay(item));
    if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).map(([key, item]) => [key, /password|secret|token|api[_-]?key|authorization/i.test(key) ? '[REDACTED]' : this.safeDisplay(item)]));
    return value;
  }
  terminal(state: string): boolean { return ['Completed', 'Failed', 'Cancelled'].includes(state); }
  stateLabel(state: string): string { return ({ Pending: 'Na fila', Running: 'Em execução', AwaitingApproval: 'Aguardando aprovação', Completed: 'Concluída', Failed: 'Falhou', Cancelled: 'Cancelada', Skipped: 'Não executado' } as Record<string, string>)[state] ?? state; }
  private message(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      if (error.status === 409) return 'A execução mudou de estado. Atualize antes de tentar novamente.';
      if (error.status === 400 || error.status === 422) return 'Dados não aceitos. Revise a tarefa e o filtro.';
      if (error.status === 404) return 'Execução não encontrada. Consulte o histórico novamente.';
      return 'Serviço indisponível. Tente novamente em instantes.';
    }
    return error instanceof Error ? error.message : 'Não foi possível concluir. Tente novamente.';
  }
  async create(): Promise<void> {
    if (this.busy()) return;
    this.error.set('');
    let metadataFilter: unknown;
    try {
      if (!this.task.trim() || this.task.trim().length > 500) throw new Error('Escreva uma tarefa com 1 a 500 caracteres.');
      metadataFilter = JSON.parse(this.filter || '{}');
      if (!metadataFilter || typeof metadataFilter !== 'object' || Array.isArray(metadataFilter) || Object.keys(metadataFilter).length > 20 || JSON.stringify(metadataFilter).length > 4000 || Object.values(metadataFilter).some(value => typeof value !== 'string')) throw new Error('Use um objeto JSON com até 20 valores de texto e 4.000 caracteres.');
    } catch (error) { this.error.set(error instanceof SyntaxError ? 'Filtro JSON inválido. Revise a sintaxe.' : this.message(error)); return; }
    this.busy.set(true);
    try {
      const result = await firstValueFrom(this.http.post<Execution>('/api/v1/executions', { task: this.task.trim(), workflow: this.workflow, portfolioId: this.portfolioId, requireApproval: this.requireApproval, metadataFilter }));
      if (this.destroyed) return;
      this.stop(); this.selected.set(result); this.events.set([]); void this.loadEvents(result.id, this.generation); this.monitor(result);
    } catch (error) { this.error.set(this.message(error)); } finally { this.busy.set(false); }
  }
  async loadHistory(): Promise<void> {
    if (this.historyBusy()) return;
    this.historyBusy.set(true); this.error.set('');
    try { this.history.set(await firstValueFrom(this.http.get<Execution[]>('/api/v1/executions?limit=20&offset=0'))); this.historyLoaded.set(true); }
    catch (error) { this.error.set(this.message(error)); } finally { this.historyBusy.set(false); }
  }
  async select(id: string): Promise<void> {
    this.stop(); const generation = this.generation; this.events.set([]); this.error.set('');
    try {
      const result = await firstValueFrom(this.http.get<Execution>(`/api/v1/executions/${encodeURIComponent(id)}`));
      if (generation !== this.generation) return;
      this.selected.set(result); void this.loadEvents(id, generation); this.monitor(result);
    } catch (error) { if (generation === this.generation) this.error.set(this.message(error)); }
  }
  async action(action: 'approve' | 'cancel'): Promise<void> {
    const selected = this.selected(); if (!selected || this.busy()) return;
    const generation = this.generation;
    this.busy.set(true); this.error.set('');
    try {
      const result = await firstValueFrom(this.http.post<Execution>(`/api/v1/executions/${encodeURIComponent(selected.id)}/${action}`, null));
      if (this.destroyed || generation !== this.generation || this.selected()?.id !== selected.id) return;
      this.stop(); this.selected.set(result); void this.loadEvents(result.id, this.generation); this.monitor(result);
    } catch (error) { if (generation === this.generation) this.error.set(this.message(error)); } finally { this.busy.set(false); }
  }
  private async loadEvents(id: string, generation: number): Promise<void> {
    const after = this.events().at(-1)?.sequence ?? 0;
    try {
      const events = await firstValueFrom(this.http.get<ExecutionEvent[]>(`/api/v1/executions/${encodeURIComponent(id)}/events?after=${after}`));
      if (generation === this.generation) this.mergeEvents(events);
    } catch (error) { if (generation === this.generation) this.error.set(this.message(error)); }
  }
  private mergeEvents(events: ExecutionEvent[]): void {
    const merged = new Map(this.events().map(event => [event.sequence, event]));
    events.forEach(event => merged.set(event.sequence, event)); this.events.set([...merged.values()].sort((a, b) => a.sequence - b.sequence));
  }
  private monitor(result: Execution): void {
    if (this.terminal(result.state)) { this.connection.set('Execução encerrada.'); return; }
    const generation = this.generation;
    this.connection.set('Acompanhando eventos em tempo real.');
    try {
      this.stream = this.openStream(`/api/v1/executions/${encodeURIComponent(result.id)}/events/stream`);
      this.stream.addEventListener('execution', event => {
        if (generation !== this.generation) return;
        try { const item = JSON.parse(event.data) as ExecutionEvent; if (item.executionId === result.id) this.mergeEvents([item]); } catch { /* Snapshot remains authoritative. */ }
        void this.refresh(result.id, generation);
      });
      this.stream.onerror = () => this.poll(result.id, generation, 0);
    } catch { this.poll(result.id, generation, 0); }
  }
  private async refresh(id: string, generation: number): Promise<void> {
    if (generation !== this.generation) return;
    if (this.refreshingGeneration === generation) { this.refreshQueued = true; return; }
    this.refreshingGeneration = generation;
    try {
      const result = await firstValueFrom(this.http.get<Execution>(`/api/v1/executions/${encodeURIComponent(id)}`));
      if (generation !== this.generation) return;
      this.selected.set(result);
      if (this.terminal(result.state)) { this.stop(); this.connection.set('Execução encerrada.'); void this.loadEvents(id, this.generation); }
    } catch (error) { if (generation === this.generation) this.error.set(this.message(error)); }
    finally {
      if (this.refreshingGeneration === generation) {
        this.refreshingGeneration = null;
        const queued = this.refreshQueued; this.refreshQueued = false;
        if (queued && generation === this.generation) void this.refresh(id, generation);
      }
    }
  }
  private poll(id: string, generation: number, attempt: number): void {
    if (generation !== this.generation) return;
    this.stream?.close(); this.stream = null;
    if (this.timer) clearTimeout(this.timer);
    if (attempt >= 60) { this.connection.set('Acompanhamento pausado. Atualize para reconectar; a execução continua no servidor.'); return; }
    this.connection.set('Conexão de eventos interrompida. Atualizando a cada 3 segundos; a execução continua no servidor.');
    this.timer = setTimeout(async () => { await this.refresh(id, generation); if (generation !== this.generation) return; await this.loadEvents(id, generation); this.poll(id, generation, attempt + 1); }, 3000);
  }
  private stop(): void { this.generation++; this.refreshingGeneration = null; this.refreshQueued = false; this.stream?.close(); this.stream = null; if (this.timer) clearTimeout(this.timer); this.timer = null; }
  ngOnDestroy(): void { this.destroyed = true; this.stop(); }
}

