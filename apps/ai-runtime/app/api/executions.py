import logging
from uuid import UUID
import psycopg
from fastapi import APIRouter, HTTPException, Query, Response
from app.executions.models import CreateExecution
from app.executions import repository as repo
from app.rag.store import KnowledgeUnavailable

router = APIRouter(prefix='/internal/v1/executions', tags=['executions'])
logger = logging.getLogger(__name__)


def call(operation):
    try:
        return operation()
    except repo.NotFound as error:
        raise HTTPException(404, 'Execution not found') from error
    except repo.Conflict as error:
        raise HTTPException(409, 'Invalid execution transition') from error
    except (psycopg.Error, KnowledgeUnavailable, ValueError) as error:
        logger.warning('Execution API unavailable: %s', type(error).__name__)
        raise HTTPException(503, 'Execution service unavailable; check database and provider configuration') from error


@router.post('', status_code=202)
def create(request: CreateExecution, response: Response):
    snapshot = call(lambda: repo.create(request))
    response.headers['Location'] = '/internal/v1/executions/' + snapshot['id']
    return snapshot


@router.get('')
def history(limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0, le=100000)):
    return call(lambda: repo.history(limit, offset))


@router.get('/{identifier}')
def get(identifier: UUID):
    return call(lambda: repo.get(str(identifier)))


@router.get('/{identifier}/events')
def events(identifier: UUID, after: int = Query(default=0, ge=0)):
    return call(lambda: repo.events(str(identifier), after))


@router.post('/{identifier}/cancel')
def cancel(identifier: UUID):
    return call(lambda: repo.transition(str(identifier), 'cancel'))


@router.post('/{identifier}/approve')
def approve(identifier: UUID):
    return call(lambda: repo.transition(str(identifier), 'approve'))
