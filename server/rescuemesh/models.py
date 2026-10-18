from __future__ import annotations
import base64
import hashlib
import json
from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MISSION = 'synthetic-flood-01'
LOCATIONS = [
    {'id': 'river-school', 'name': 'River School', 'x': 25, 'y': 64},
    {'id': 'east-bridge', 'name': 'East Bridge', 'x': 65, 'y': 40},
    {'id': 'hill-clinic', 'name': 'Hill Clinic', 'x': 78, 'y': 15},
]
LOCATION_IDS = {x['id'] for x in LOCATIONS}

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Claim(Strict):
    subject: str = Field(min_length=1, max_length=100)
    predicate: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=200)

class Fact(Strict):
    text: str = Field(min_length=1, max_length=600)
    supporting_event_ids: list[UUID] = Field(min_length=1, max_length=16)

class Conflict(Strict):
    text: str = Field(min_length=1, max_length=600)
    supporting_event_ids: list[UUID] = Field(min_length=1, max_length=16)

class Response(Strict):
    action: str = Field(min_length=1, max_length=1000)
    prerequisites: list[str] = Field(min_length=1, max_length=8)
    resource_id: Literal['rescue-team-1', 'supply-van-1', 'none']
    supporting_event_ids: list[UUID] = Field(min_length=1, max_length=16)

class Assessment(Strict):
    observed_facts: list[Fact] = Field(max_length=16)
    uncertain_or_conflicting_claims: list[Conflict] = Field(min_length=1, max_length=16)
    missing_information: list[str] = Field(min_length=1, max_length=8)
    next_question: str = Field(min_length=1, max_length=600)
    proposed_response: Response

class Payload(Strict):
    incident_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,80}$')
    location_id: Literal['river-school', 'east-bridge', 'hill-clinic']
    text: str | None = Field(default=None, min_length=1, max_length=2000)
    claims: list[Claim] = Field(default_factory=list, max_length=8)
    assessment: Assessment | None = None
    provider: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=100)
    evidence_revision: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')
    receipt_event_ids: list[UUID] = Field(default_factory=list, max_length=32)

class Event(Strict):
    schema_version: Literal[1]
    event_id: UUID
    mission_id: Literal['synthetic-flood-01']
    origin_device_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    origin_sequence: int = Field(gt=0, le=2**53-1, strict=True)
    event_type: Literal['observation', 'question', 'answer', 'assessment', 'proposal', 'approval', 'delivery-receipt']
    created_at: datetime
    referenced_event_ids: list[UUID] = Field(max_length=32)
    payload: Payload

    @field_validator('event_id', mode='before')
    @classmethod
    def canonical_event_id(cls, value):
        if isinstance(value, str) and str(UUID(value)) != value:
            raise ValueError('UUID must be canonical lowercase')
        return value

    @field_validator('referenced_event_ids', mode='before')
    @classmethod
    def canonical_refs(cls, value):
        if any(isinstance(x, str) and str(UUID(x)) != x for x in value):
            raise ValueError('UUID references must be canonical lowercase')
        return value

    @field_validator('created_at', mode='before')
    @classmethod
    def timestamp_string(cls, value):
        if not isinstance(value, (str, datetime)):
            raise ValueError('RFC3339 timestamp required')
        return value

    @field_validator('created_at')
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError('created_at must include timezone')
        return value

    @model_validator(mode='after')
    def semantic(self):
        if self.event_type in ['observation', 'question', 'answer'] and not self.payload.text:
            raise ValueError('text required')
        if self.event_type == 'answer' and not self.referenced_event_ids:
            raise ValueError('answer must reference question')
        if self.event_type in ['assessment', 'proposal']:
            if not all([self.payload.assessment, self.payload.provider, self.payload.model, self.payload.evidence_revision]):
                raise ValueError('model output must include provenance and revision')
        if self.event_type == 'delivery-receipt' and not self.payload.receipt_event_ids:
            raise ValueError('receipt IDs required')
        return self

class Envelope(Strict):
    event_b64: str = Field(max_length=16384)
    signature_b64: str = Field(max_length=120)

    def decoded(self) -> tuple[bytes, bytes, Event]:
        raw = base64.b64decode(self.event_b64, validate=True)
        sig = base64.b64decode(self.signature_b64, validate=True)
        if len(raw) > 12288:
            raise ValueError('event too large')
        # Reject duplicate JSON keys: differing parsers must not interpret signed bytes differently.
        def pairs(xs):
            d = {}
            for k, v in xs:
                if k in d:
                    raise ValueError('duplicate JSON key')
                d[k] = v
            return d
        data = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs)
        return raw, sig, Event.model_validate(data)

class SyncBatch(Strict):
    events: list[Envelope] = Field(min_length=1, max_length=32)

class Approve(Strict):
    evidence_revision: str = Field(pattern=r'^[a-f0-9]{64}$')
    prerequisites_confirmed: Literal[True]

def evidence_revision(events: list[dict]) -> str:
    ids = sorted(x['event_id'] for x in events if x['event_type'] in ['observation', 'answer'])
    return hashlib.sha256('\n'.join(ids).encode()).hexdigest()

def validate_assessment(a: Assessment, evidence: list[dict]):
    ids = {x['event_id'] for x in evidence}
    cited = [i for f in a.observed_facts + a.uncertain_or_conflicting_claims for i in f.supporting_event_ids]
    cited += a.proposed_response.supporting_event_ids
    if not ids or any(str(i) not in ids for i in cited):
        raise ValueError('unknown or empty supporting evidence')
    # An inferred response cannot establish a route's safety.
    text = a.proposed_response.action.lower()
    if any(x in text for x in ['route is safe', 'bridge is safe', 'building is safe']):
        raise ValueError('safety must remain unconfirmed')
    return a
