from datetime import datetime, timezone
import uuid
from .models import evidence_revision, validate_assessment
from .central_events import approval_event

def now():
    return datetime.now(timezone.utc).isoformat()

def ingest(state, verified, envelopes, gateway):
    accepted = []
    for event, envelope in zip(verified, envelopes):
        eid = event['event_id']
        old = state['events'].get(eid)
        if old:
            if old['envelope']['event_b64'] != envelope['event_b64']:
                raise ValueError('event ID collision')
        else:
            for record in state['events'].values():
                existing = record['event']
                if (existing['origin_device_id'], existing['origin_sequence']) == (event['origin_device_id'], event['origin_sequence']):
                    raise ValueError('origin sequence collision')
                if existing['payload']['incident_id'] == event['payload']['incident_id'] and existing['payload']['location_id'] != event['payload']['location_id']:
                    raise ValueError('incident location is immutable')
            state['events'][eid] = {'event': event, 'envelope': envelope, 'received_at': now(), 'gateway_device_id': gateway}
        accepted.append(eid)
    receipt = {'gateway_device_id': gateway, 'event_ids': sorted(set(accepted)), 'received_at': now()}
    # Bound repeated upload audit records; repeated uploads are otherwise idempotent.
    if not any(r['gateway_device_id'] == gateway and r['event_ids'] == receipt['event_ids'] for r in state['receipts']):
        state['receipts'] = (state['receipts'] + [receipt])[-100:]
    return {'accepted_event_ids': accepted, 'durable': True, 'server_time': now()}

def incidents(state):
    groups = {}
    for r in state['events'].values():
        e = r['event']; p = e['payload']; iid = p['incident_id']
        g = groups.setdefault(iid, {'id': iid, 'location_id': p['location_id'], 'evidence': [], 'events': [], 'conflicts': [], 'proposals': [], 'approvals': []})
        g['events'].append(r)
        if e['event_type'] in ['observation', 'answer']:
            g['evidence'].append(e)
    for g in groups.values():
        g['evidence'].sort(key=lambda e: e['event_id'])
        g['evidence_revision'] = evidence_revision(g['evidence'])
        claims = {}
        for e in g['evidence']:
            for c in e['payload'].get('claims', []):
                claims.setdefault((c['subject'].lower().strip(), c['predicate'].lower().strip()), []).append((c['value'].lower().strip(), e['event_id']))
        for (subject, predicate), values in claims.items():
            known_values = [x for x in values if x[0] not in {'unknown', 'unverified', 'uncertain', 'not known'}]
            if len({x[0] for x in known_values}) > 1:
                g['conflicts'].append({'text': f'Conflicting reported {subject} / {predicate}', 'supporting_event_ids': [x[1] for x in known_values], 'values': [x[0] for x in known_values], 'provider': 'claim comparison (not AI)'})
        g['proposals'] = [dict(p, stale=p['evidence_revision'] != g['evidence_revision']) for p in state['proposals'].values() if p['incident_id'] == g['id']]
        g['approvals'] = [a for a in state['approvals'].values() if a['incident_id'] == g['id']]
        g['last_received_at'] = max(r['received_at'] for r in g['events'])
    return sorted(groups.values(), key=lambda g: g['last_received_at'], reverse=True)

def save_proposal(state, iid, revision, assessment, provider, model):
    g = next((g for g in incidents(state) if g['id'] == iid), None)
    if not g or g['evidence_revision'] != revision:
        raise ValueError('evidence changed during inference; reassess')
    validate_assessment(assessment, g['evidence'])
    pid = str(uuid.uuid4())
    p = {'id': pid, 'incident_id': iid, 'evidence_revision': revision, 'assessment': assessment.model_dump(mode='json'), 'provider': provider, 'model': model, 'created_at': now(), 'status': 'proposed'}
    state['proposals'][pid] = p
    if len(state['proposals']) > 64:
        raise ValueError('proposal capacity reached')
    return p

def approve(state, pid, revision, actor):
    p = state['proposals'].get(pid)
    if not p:
        raise KeyError('proposal not found')
    if pid in state['approvals']:
        if state['approvals'][pid]['evidence_revision'] != revision:
            raise ValueError('revision mismatch')
        return state['approvals'][pid]
    g = next(g for g in incidents(state) if g['id'] == p['incident_id'])
    if p['evidence_revision'] != revision or revision != g['evidence_revision']:
        raise ValueError('stale proposal: reassess before approving')
    resource = p['assessment']['proposed_response']['resource_id']
    if resource != 'none' and resource in state['assignments']:
        raise ValueError('resource already centrally assigned')
    timestamp=now(); eid=str(uuid.uuid4())
    a = {'proposal_id': pid, 'incident_id': p['incident_id'], 'evidence_revision': revision, 'actor': actor, 'approved_at': timestamp, 'resource_id': resource, 'prerequisites_confirmed': True, 'approval_event_id': eid}
    state['events'][eid]=approval_event(state,a,p,g['location_id'],timestamp,eid)
    state['approvals'][pid] = a
    if resource != 'none':
        state['assignments'][resource] = a
    p['status'] = 'approved'
    return a
