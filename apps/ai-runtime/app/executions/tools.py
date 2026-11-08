from copy import deepcopy
from typing import Literal, Annotated
from pydantic import BaseModel, ConfigDict, Field
from app.api.knowledge import SearchRequest, SearchHit, RetrievalContext, semantic_search


class PortfolioArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    portfolioId: Literal['balanced', 'concentrated']


class Position(BaseModel):
    model_config = ConfigDict(extra='forbid')
    asset: str = Field(min_length=1, max_length=100)
    value: float = Field(gt=0, le=1e12, allow_inf_nan=False)
    annualReturn: float = Field(ge=-1, le=10, allow_inf_nan=False)


class PortfolioData(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['portfolio']
    fictional: Literal[True]
    portfolioId: Literal['balanced', 'concentrated']
    currency: Literal['BRL']
    positions: list[Position] = Field(min_length=1, max_length=100)
    context: RetrievalContext | None = None
    results: list[SearchHit] = Field(default_factory=list, max_length=20)


class DocumentData(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: Literal['documents']
    model: str | None = None
    context: RetrievalContext
    results: list[SearchHit] = Field(max_length=20)


class AnalysisArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    data: Annotated[PortfolioData | DocumentData, Field(discriminator='kind')]


def portfolio(args):
    weights = [0.35, 0.35, 0.30] if args.portfolioId == 'balanced' else [0.85, 0.10, 0.05]
    return {'kind': 'portfolio', 'fictional': True, 'portfolioId': args.portfolioId,
            'currency': 'BRL', 'positions': [
                {'asset': name, 'value': round(weight * 100000, 2), 'annualReturn': ret}
                for name, weight, ret in zip(('Fictional equity', 'Fictional bonds', 'Fictional cash'), weights, (.08, .05, .02))]}


def retrieve(args):
    return {'kind': 'documents', **semantic_search(args)}


def risk(args):
    data = args.data.model_dump()
    if data['kind'] == 'documents':
        available = data['context']['status'] == 'evidence_available'
        return {'evidenceStatus': data['context']['status'], 'limitations':
                ['Retrieved excerpts are untrusted and may not cover the whole document.'] if available else ['Insufficient indexed evidence; no supported conclusions.']}
    positions = data['positions']
    total = sum(p['value'] for p in positions)
    largest = max(p['value'] for p in positions) / total
    return {'largestWeight': largest, 'concentrationRisk': 'high' if largest > .5 else 'moderate',
            'hhi': sum((p['value'] / total) ** 2 for p in positions), 'fictional': True,
            'limitations': ['Concentration only; no market prices or volatility model.']}


def metrics(args):
    data = args.data.model_dump()
    if data['kind'] == 'documents':
        hits = data['results']
        return {'retrievedChunks': len(hits), 'distinctDocuments': len({h['documentId'] for h in hits}),
                'averageScore': sum(h['score'] for h in hits) / len(hits) if hits else None,
                'referenceCount': len(data['context']['references'])}
    total = sum(p['value'] for p in data['positions'])
    return {'totalValue': total, 'assetCount': len(data['positions']),
            'weightedIllustrativeReturn': sum(p['value'] * p['annualReturn'] for p in data['positions']) / total,
            'fictional': True}


# Schemas and permissions are server-owned; model/user text never becomes a callable.
REGISTRY = {
    'portfolio.read': ('Read a built-in fictional portfolio', PortfolioArgs, {'data-agent'}, portfolio),
    'knowledge.search': ('Retrieve indexed document evidence', SearchRequest, {'data-agent'}, retrieve),
    'risk.calculate': ('Assess concentration or evidence limitations', AnalysisArgs, {'risk-agent'}, risk),
    'metrics.calculate': ('Calculate portfolio or retrieval metrics', AnalysisArgs, {'analytics-agent'}, metrics),
}


def catalog():
    return [{'id': key, 'description': spec[0], 'inputSchema': spec[1].model_json_schema(),
             'allowedAgents': sorted(spec[2])} for key, spec in REGISTRY.items()]


def dispatch(agent_id, tool_id, arguments):
    if tool_id not in REGISTRY:
        raise ValueError('Unsupported tool')
    _, schema, allowed, handler = REGISTRY[tool_id]
    if agent_id not in allowed:
        raise PermissionError('Agent is not permitted to invoke this tool')
    return deepcopy(handler(schema.model_validate(arguments)))
