import { Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

export interface BankTimelineItem { date: string; category: string; description: string; source: string; }
export interface BankCustomer {
  id: string; displayName: string; segment: string; caseStatus: string; riskIndicator: string;
  relationshipSince: string; lastReviewAt: string; summary: string; reviewFlags: string[];
  timeline: BankTimelineItem[]; synthetic: boolean;
}
interface AnalysisReceipt { id: string; state: string; provider: string; requireApproval: boolean; }

@Component({
  selector: 'app-bank-operations',
  imports: [DatePipe],
  templateUrl: './bank-operations.html',
  styleUrl: './bank-operations.css'
})
export class BankOperations implements OnInit {
  private readonly http = inject(HttpClient);
  readonly customers = signal<BankCustomer[]>([]);
  readonly selected = signal<BankCustomer | null>(null);
  readonly loading = signal(true);
  readonly error = signal('');
  readonly starting = signal(false);
  readonly analysis = signal<AnalysisReceipt | null>(null);
  readonly analysisError = signal('');

  ngOnInit(): void { void this.load(); }

  async load(): Promise<void> {
    this.loading.set(true); this.error.set('');
    try {
      const customers = await firstValueFrom(this.http.get<BankCustomer[]>('/api/v1/bank/customers'));
      this.customers.set(customers);
      this.selected.set(customers[0] ?? null);
    } catch (error) {
      this.error.set(error instanceof HttpErrorResponse && error.status === 401
        ? 'Sua sessão não permite consultar clientes. Solicite acesso ao responsável.'
        : 'Não foi possível carregar os casos. Verifique a API e tente novamente.');
    } finally { this.loading.set(false); }
  }

  async startAnalysis(): Promise<void> {
    const customer = this.selected();
    if (!customer || this.starting()) return;
    this.starting.set(true); this.analysisError.set(''); this.analysis.set(null);
    try {
      this.analysis.set(await firstValueFrom(this.http.post<AnalysisReceipt>(
        `/api/v1/bank/customers/${encodeURIComponent(customer.id)}/analysis`,
        { question: 'Resuma o histórico, identifique riscos e cite as fontes utilizadas.' })));
    } catch (error) {
      this.analysisError.set(error instanceof HttpErrorResponse && error.status === 403
        ? 'Você não possui permissão para iniciar esta análise.'
        : 'A análise não pôde ser iniciada. Verifique o serviço e tente novamente.');
    } finally { this.starting.set(false); }
  }
}
