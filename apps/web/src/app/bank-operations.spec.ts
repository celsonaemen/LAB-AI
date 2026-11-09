import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { BankOperations } from './bank-operations';

describe('BankOperations', () => {
  const customer = {id:'CUS-FIC-1042',displayName:'Aurora Têxtil Ltda.',segment:'Empresas',caseStatus:'Revisão necessária',riskIndicator:'Elevado',relationshipSince:'2021-03-18',lastReviewAt:'2026-10-28',summary:'Caso sintético.',reviewFlags:['Cadastro divergente'],timeline:[],synthetic:true};
  let http: HttpTestingController;
  beforeEach(async () => {
    await TestBed.configureTestingModule({imports:[BankOperations],providers:[provideHttpClient(),provideHttpClientTesting()]}).compileComponents();
    http=TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('starts the selected customer analysis through the bank boundary', async () => {
    const fixture=TestBed.createComponent(BankOperations); fixture.detectChanges();
    http.expectOne('/api/v1/bank/customers').flush([customer]);
    await fixture.whenStable(); fixture.detectChanges();
    const button=Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('button')).find(item=>item.textContent?.includes('Iniciar análise'));
    expect(button).toBeDefined(); button?.click();
    const request=http.expectOne('/api/v1/bank/customers/CUS-FIC-1042/analysis');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({question:'Resuma o histórico, identifique riscos e cite as fontes utilizadas.'});
    request.flush({id:'run-42',task:'Cliente fictício',workflow:'document-review',portfolioId:'concentrated',state:'Pending',agents:[],createdAt:'2026-11-08T12:00:00Z',startedAt:null,finishedAt:null,durationMs:null,result:null,error:null,provider:'deterministic',requireApproval:true});
    await fixture.whenStable(); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('run-42');
    expect(fixture.nativeElement.textContent).toContain('aprovação humana');
  });
});
