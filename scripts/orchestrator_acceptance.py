"""Real HTTP agent acceptance. Requires .NET, runtime worker and native pgvector.

No mocks/providers are installed by this script. It checks the provider label,
retains fictional documents/executions and saves the observed events/results.
"""
import argparse
import json
import time
from pathlib import Path
from uuid import uuid4

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:5080')
    parser.add_argument('--output', default='.artifacts/orchestrator')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    corpus = str(uuid4())
    evidence = {'baseUrl': args.base_url, 'corpus': corpus, 'runs': [], 'checks': []}
    with httpx.Client(base_url=args.base_url, timeout=150) as client:
        def call(method, path, payload=None, expected=200):
            response = client.request(method, path, json=payload) if payload is not None else client.request(method, path)
            assert response.status_code == expected, (path, response.status_code, response.text[:600])
            return response.json()

        def create(**overrides):
            return call('POST', '/api/v1/executions', {
                'task': 'Analise os riscos de crédito e as garantias da carteira fictícia.',
                'workflow': 'portfolio-review', 'portfolioId': 'concentrated',
                'requireApproval': False, 'metadataFilter': {'acceptanceRun': corpus}, **overrides}, 202)

        def wait(identifier, expected):
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                snapshot = call('GET', '/api/v1/executions/' + identifier)
                if snapshot['state'] == expected:
                    return snapshot
                assert snapshot['state'] not in ('Failed', 'Cancelled', 'Completed'), snapshot
                time.sleep(0.25)
            raise AssertionError(f'Execution {identifier} did not reach {expected}')

        def events(identifier):
            result = call('GET', f'/api/v1/executions/{identifier}/events?after=0')
            assert result and all(e['executionId'] == identifier for e in result)
            seq = [e['sequence'] for e in result]
            assert seq == sorted(set(seq))
            return result

        document = call('POST', '/api/v1/knowledge/documents', {
            'title': 'Stage 2 fictional credit evidence', 'source': 'demo/stage2-credit.md',
            'text': 'A política fictícia exige garantias para reduzir perdas por inadimplência. '
                    'Credit policy requires collateral to reduce borrower default losses. Corpus ' + corpus,
            'metadata': {'acceptanceRun': corpus}}, 201)

        approved = create(requireApproval=True)
        paused = wait(approved['id'], 'AwaitingApproval')
        assert [a['id'] for a in paused['agents']] == ['data-agent', 'risk-agent', 'analytics-agent', 'report-agent']
        assert all(a['state'] == 'Completed' for a in paused['agents'][:3])
        assert paused['agents'][3]['state'] != 'Completed'
        call('POST', f"/api/v1/executions/{approved['id']}/approve")
        completed = wait(approved['id'], 'Completed')
        assert all(a['state'] == 'Completed' and a['result'] is not None for a in completed['agents'])
        assert completed['startedAt'] and completed['finishedAt'] and completed['durationMs'] >= 0
        assert completed['provider'] in ('deterministic', 'ollama')
        assert completed['result'] is not None
        trace = events(completed['id'])
        trace_text = json.dumps(trace)
        assert 'tool' in trace_text.lower(), 'No tool trace recorded'
        assert document['documentId'] in trace_text, 'No actual RAG document reference recorded'
        evidence['runs'].append({'snapshot': completed, 'events': trace})
        evidence['checks'].extend(['four_agents_dependency_order', 'approval_pause_resume', 'real_tool_execution', 'real_rag_source', 'duration_and_final_result'])

        # Replay a terminal stream so the server must deliver durable events then close.
        after = trace[-3]['sequence']
        with client.stream('GET', f"/api/v1/executions/{completed['id']}/events/stream", headers={'Last-Event-ID': str(after)}) as stream:
            assert stream.status_code == 200 and 'text/event-stream' in stream.headers['content-type']
            ids = [int(line[3:].strip()) for line in stream.iter_lines() if line.startswith('id:')]
        assert ids == [event['sequence'] for event in trace if event['sequence'] > after], ids
        evidence['checks'].append('sse_persisted_replay_and_terminal_close')
        call('POST', f"/api/v1/executions/{completed['id']}/cancel", expected=409)

        review = create(workflow='document-review')
        reviewed = wait(review['id'], 'Completed')
        review_events = events(reviewed['id'])
        assert document['documentId'] in json.dumps(review_events)
        evidence['runs'].append({'snapshot': reviewed, 'events': review_events})

        missing = create(workflow='document-review', metadataFilter={'acceptanceRun': str(uuid4())})
        insufficient = wait(missing['id'], 'Completed')
        assert 'insufficient_evidence' in json.dumps(insufficient), insufficient
        evidence['runs'].append({'snapshot': insufficient, 'events': events(insufficient['id'])})
        evidence['checks'].extend(['document_workflow', 'insufficient_evidence_without_fabrication'])

        cancellable = create(requireApproval=True)
        wait(cancellable['id'], 'AwaitingApproval')
        cancelled = call('POST', f"/api/v1/executions/{cancellable['id']}/cancel")
        assert cancelled['state'] == 'Cancelled'
        assert cancelled['agents'][3]['state'] != 'Completed'
        call('POST', f"/api/v1/executions/{cancellable['id']}/approve", expected=409)
        evidence['runs'].append({'snapshot': cancelled, 'events': events(cancelled['id'])})
        evidence['checks'].append('cancellation_and_terminal_guards')

        history = call('GET', '/api/v1/executions?limit=100&offset=0')
        assert {r['snapshot']['id'] for r in evidence['runs']} <= {r['id'] for r in history}
        call('POST', '/api/v1/executions', {'task': 'demo', 'workflow': 'shell-execution'}, 400)
        call('GET', '/api/v1/executions/' + str(uuid4()), expected=404)
        evidence['checks'].extend(['persisted_history_and_events', 'workflow_allowlist', 'missing_execution_404'])
    evidence['passed'] = True
    (output / 'acceptance.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'checks': evidence['checks'], 'executionIds': [r['snapshot']['id'] for r in evidence['runs']],
                      'providers': list({r['snapshot']['provider'] for r in evidence['runs']}), 'evidence': str(output / 'acceptance.json')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
