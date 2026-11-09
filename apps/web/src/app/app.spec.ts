import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting, HttpTestingController } from '@angular/common/http/testing';
import { App } from './app';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [App], providers: [provideHttpClient(), provideHttpClientTesting()] }).compileComponents();
  });
  afterEach(() => TestBed.inject(HttpTestingController).verify());
  it('should create the app', () => expect(TestBed.createComponent(App).componentInstance).toBeTruthy());
  it('should render title', () => {
    const fixture = TestBed.createComponent(App); fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).querySelector('h1')?.textContent).toContain('AEGIS AGENT LAB');
  });
  it('offers a dedicated fictional-bank customer analysis workspace', async () => {
    const fixture = TestBed.createComponent(App); fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    const bankButton = Array.from(root.querySelectorAll('button')).find(button => button.textContent?.includes('Análise de clientes'));
    expect(bankButton).toBeDefined();
    bankButton?.click(); fixture.detectChanges();
    const request = TestBed.inject(HttpTestingController).expectOne('/api/v1/bank/customers');
    request.flush([{id:'CUS-FIC-1042',displayName:'Aurora Têxtil Ltda.',segment:'Empresas',caseStatus:'Revisão necessária',riskIndicator:'Elevado',relationshipSince:'2021-03-18',lastReviewAt:'2026-10-28',summary:'Caso sintético.',reviewFlags:['Cadastro divergente'],timeline:[],synthetic:true}]);
    await fixture.whenStable(); fixture.detectChanges();
    expect(root.textContent).toContain('Aurora Têxtil Ltda.');
    expect(root.textContent).toContain('Dados 100% sintéticos');
  });
  it('searches only through the gateway and displays evidence as plain text', async () => {
    const fixture = TestBed.createComponent(App); fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    await fixture.whenStable(); const query = root.querySelector<HTMLInputElement>('#query');
    expect(query).not.toBeNull(); if (!query) return;
    query.value = 'garantias'; query.dispatchEvent(new Event('input')); fixture.detectChanges();
    root.querySelector<HTMLFormElement>('#search-form')!.dispatchEvent(new Event('submit'));
    const request = TestBed.inject(HttpTestingController).expectOne('/api/v1/knowledge/search');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({query:'garantias', top_k:5, minScore:0.35, metadataFilter:{}, maxContextChars:6000});
    request.flush({model:'test', dimensions:384, results:[{documentId:'doc-1',chunkId:'chunk-1',title:'Política',source:'policy.md',ordinal:0,content:'<script>unsafe</script> garantias',score:0.8,metadata:{area:'risco'},filename:'policy.md'}],context:{status:'ready',text:'garantias',references:[],generatedAnswer:null}});
    await fixture.whenStable(); fixture.detectChanges();
    expect(root.textContent).toContain('chunk-1'); expect(root.textContent).toContain('policy.md');
    expect(root.textContent).toContain('<script>unsafe</script>'); expect(root.querySelector('script')).toBeNull();
  });
  it('reports unavailable retrieval and permits another attempt', async () => {
    const fixture = TestBed.createComponent(App); fixture.detectChanges(); const root = fixture.nativeElement as HTMLElement;
    await fixture.whenStable(); const query = root.querySelector<HTMLInputElement>('#query'); expect(query).not.toBeNull(); if (!query) return;
    query.value='risco'; query.dispatchEvent(new Event('input')); fixture.detectChanges();
    root.querySelector<HTMLFormElement>('#search-form')!.dispatchEvent(new Event('submit'));
    TestBed.inject(HttpTestingController).expectOne('/api/v1/knowledge/search').flush({}, {status:503,statusText:'Unavailable'});
    await fixture.whenStable(); fixture.detectChanges(); expect(root.querySelector('[role="alert"]')?.textContent).toContain('Tente novamente');
    expect(root.querySelector<HTMLButtonElement>('#search-button')!.disabled).toBeFalse();
  });
  it('rejects unsupported files before sending a request', () => {
    const fixture = TestBed.createComponent(App); fixture.detectChanges(); const root = fixture.nativeElement as HTMLElement;
    const input = root.querySelector<HTMLInputElement>('#file'); expect(input).not.toBeNull(); if (!input) return;
    const files = new DataTransfer(); files.items.add(new File(['x'],'unsafe.exe')); input.files=files.files; input.dispatchEvent(new Event('change')); fixture.detectChanges();
    expect(root.querySelector('[role="alert"]')?.textContent).toContain('PDF');
    TestBed.inject(HttpTestingController).expectNone('/api/v1/knowledge/documents');
  });
  it('uploads UTF-8 file bytes and renders the duplicate receipt', async () => {
    const fixture = TestBed.createComponent(App); fixture.detectChanges(); await fixture.whenStable();
    const app = fixture.componentInstance;
    const input = (fixture.nativeElement as HTMLElement).querySelector<HTMLInputElement>('#file')!;
    const files = new DataTransfer(); files.items.add(new File(['ação'], 'policy.md')); input.files=files.files; input.dispatchEvent(new Event('change'));
    app.metadata='{"area":"risco"}';
    const originalRead = FileReader.prototype.readAsDataURL;
    let readComplete!: () => void;
    const readDone = new Promise<void>(resolve => { readComplete = resolve; });
    spyOn(FileReader.prototype, 'readAsDataURL').and.callFake(function(this: FileReader, blob: Blob) {
      this.addEventListener('loadend', readComplete, { once: true }); originalRead.call(this, blob);
    });
    const pending=app.upload();
    await readDone; await Promise.resolve();
    const request=TestBed.inject(HttpTestingController).expectOne('/api/v1/knowledge/documents');
    expect(request.request.body).toEqual({title:'policy.md',source:'policy.md',filename:'policy.md',contentBase64:'YcOnw6Nv',metadata:{area:'risco'}});
    request.flush({documentId:'existing-doc',chunks:2,deduplicated:true,model:'test'});
    await pending; fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Documento já existente');
    expect(fixture.nativeElement.textContent).toContain('existing-doc');
  });
  it('shows insufficient evidence and validates metadata without a network call', async () => {
    const fixture=TestBed.createComponent(App); fixture.detectChanges(); const app=fixture.componentInstance;
    app.query='garantias'; app.filter='[]'; await app.search();
    TestBed.inject(HttpTestingController).expectNone('/api/v1/knowledge/search'); expect(app.searchError()).toContain('objeto JSON');
    app.filter='{}'; const pending=app.search();
    TestBed.inject(HttpTestingController).expectOne('/api/v1/knowledge/search').flush({model:'test',dimensions:384,results:[],context:{status:'insufficient_evidence',text:'',references:[],generatedAnswer:null}});
    await pending; fixture.detectChanges(); expect(fixture.nativeElement.textContent).toContain('Evidência insuficiente');
  });});




