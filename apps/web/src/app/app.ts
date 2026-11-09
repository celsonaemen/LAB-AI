import { Component, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { DecimalPipe, JsonPipe } from '@angular/common';
import { firstValueFrom } from 'rxjs';
import { Executions } from './executions';
import { BankOperations } from './bank-operations';

interface Receipt { documentId: string; chunks: number; deduplicated: boolean; model: string; status?: string; metadata?: Record<string, string>; }
interface Hit { documentId: string; chunkId: string; title: string; source: string; ordinal: number; content: string; score: number; metadata: Record<string, unknown>; filename: string | null; }
interface SearchResponse { model: string; dimensions: number; results: Hit[]; context: { status: string; text: string; references: unknown[]; generatedAnswer: null }; }
@Component({ selector: 'app-root', imports: [FormsModule, DecimalPipe, JsonPipe, Executions, BankOperations], templateUrl: './app.html', styleUrl: './app.css' })
export class App {
  readonly section = signal<'bank' | 'knowledge' | 'agents'>('knowledge');
  private readonly http = inject(HttpClient);
  title = ''; source = ''; metadata = '{}'; query = ''; topK = 5; minScore = 0.35; filter = '{}';
  file: File | null = null;
  readonly uploading = signal(false); readonly searching = signal(false);
  readonly uploadError = signal(''); readonly searchError = signal('');
  readonly receipt = signal<Receipt | null>(null); readonly response = signal<SearchResponse | null>(null);

  selectFile(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.file = null; this.receipt.set(null); this.uploadError.set('');
    const file = input.files?.[0]; if (!file) return;
    if (!/\.(pdf|txt|md|markdown)$/i.test(file.name) || file.size === 0 || file.size > 2_000_000) {
      this.uploadError.set('Escolha um arquivo PDF, TXT ou Markdown não vazio de até 2 MB.'); input.value = ''; return;
    }
    this.file = file; if (!this.title) this.title = file.name; if (!this.source) this.source = file.name;
  }
  private jsonObject(value: string): Record<string, unknown> {
    const parsed: unknown = JSON.parse(value || '{}');
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('Use um objeto JSON, por exemplo: {"area":"risco"}.');
        if (Object.keys(parsed).length > 20 || JSON.stringify(parsed).length > 4000 || Object.values(parsed).some(value => typeof value !== 'string')) {
      throw new Error('Use até 20 metadados com valores de texto e no máximo 4.000 caracteres.');
    }
    return parsed as Record<string, unknown>;
  }
  private errorMessage(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      if (error.status === 400 || error.status === 422) return 'Dados não aceitos. Revise o arquivo e os campos e tente novamente.';
      if (error.status === 504) return 'O processamento excedeu o tempo disponível. Tente novamente.';
      return 'Serviço indisponível no momento. Tente novamente em instantes.';
    }
    return error instanceof Error ? error.message : 'Não foi possível concluir. Tente novamente.';
  }
  async upload(): Promise<void> {
    if (this.uploading() || !this.file) return;
    this.uploadError.set(''); this.receipt.set(null);
    let metadata: Record<string, unknown>;
    try { metadata = this.jsonObject(this.metadata); } catch (error) { this.uploadError.set(this.errorMessage(error)); return; }
    if (!this.title.trim() || !this.source.trim()) { this.uploadError.set('Preencha o título e a origem.'); return; }
    this.uploading.set(true);
    try {
      const file = this.file;
      const contentBase64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result).split(',')[1]);
        reader.onerror = () => reject(new Error('Não foi possível ler o arquivo. Selecione-o novamente.'));
        reader.readAsDataURL(file);
      });
      this.receipt.set(await firstValueFrom(this.http.post<Receipt>('/api/v1/knowledge/documents', { title: this.title.trim(), source: this.source.trim(), filename: file.name, contentBase64, metadata })));
    } catch (error) { this.uploadError.set(this.errorMessage(error)); } finally { this.uploading.set(false); }
  }
  async search(): Promise<void> {
    if (this.searching()) return;
    this.searchError.set(''); this.response.set(null);
    if (!this.query.trim()) { this.searchError.set('Escreva o que deseja encontrar.'); return; }
    if (!Number.isInteger(this.topK) || this.topK < 1 || this.topK > 20 || !Number.isFinite(this.minScore) || this.minScore < -1 || this.minScore > 1) { this.searchError.set('Use 1 a 20 resultados e similaridade entre -1 e 1.'); return; }
    let metadataFilter: Record<string, unknown>;
    try { metadataFilter = this.jsonObject(this.filter); } catch (error) { this.searchError.set(this.errorMessage(error)); return; }
    this.searching.set(true);
    try { this.response.set(await firstValueFrom(this.http.post<SearchResponse>('/api/v1/knowledge/search', { query: this.query.trim(), top_k: this.topK, minScore: this.minScore, metadataFilter, maxContextChars: 6000 }))); }
    catch (error) { this.searchError.set(this.errorMessage(error)); } finally { this.searching.set(false); }
  }
}

