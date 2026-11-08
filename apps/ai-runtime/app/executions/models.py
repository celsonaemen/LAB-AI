import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

AGENTS = ('data-agent', 'risk-agent', 'analytics-agent', 'report-agent')
TERMINAL = ('Completed', 'Failed', 'Cancelled')


class CreateExecution(BaseModel):
    model_config = ConfigDict(extra='forbid')
    task: str = Field(min_length=1, max_length=500)
    workflow: Literal['portfolio-review', 'document-review']
    portfolioId: Literal['balanced', 'concentrated'] = 'balanced'
    requireApproval: bool = False
    metadataFilter: dict[str, str] = Field(default_factory=dict)

    @field_validator('task')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('Task must not be blank')
        return value.strip()

    @field_validator('metadataFilter')
    @classmethod
    def bounded(cls, value):
        if len(value) > 20 or len(json.dumps(value)) > 4000:
            raise ValueError('Metadata filter exceeds bounds')
        return value
