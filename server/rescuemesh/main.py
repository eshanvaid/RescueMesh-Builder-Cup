import asyncio
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from . import ai, service
from .models import SyncBatch, Approve, LOCATIONS, MISSION
from .security import load_json, token_role, verify
from .store import SQLiteStore, FirestoreStore

def create_app(store=None, trust=None, auth=None):
    app = FastAPI(title='RescueMesh', version='0.1.0')
    store = store or (FirestoreStore(os.getenv('GOOGLE_CLOUD_PROJECT')) if os.getenv('RESCUEMESH_STORE') == 'firestore' else SQLiteStore(os.getenv('RESCUEMESH_DB', 'local-demo/rescuemesh.db')))
    trust = trust if trust is not None else load_json(os.getenv('RESCUEMESH_TRUST_FILE', 'local-demo/trust.json'))
    auth = auth if auth is not None else load_json(os.getenv('RESCUEMESH_AUTH_FILE', 'local-demo/auth.json'))
    local_auth = os.getenv('RESCUEMESH_LOCAL_AUTH', 'false') == 'true' and not os.getenv('K_SERVICE')

    @app.middleware('http')
    async def body_limit(request: Request, call_next):
        if request.method in ['POST', 'PUT', 'PATCH']:
            total = 0; chunks = []
            async for chunk in request.stream():
                total += len(chunk)
                if total > 512000:
                    return __import__('starlette.responses', fromlist=['JSONResponse']).JSONResponse({'detail': 'request too large'}, status_code=413)
                chunks.append(chunk)
            request._body = b''.join(chunks)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Cache-Control'] = 'no-store'
        return response

    async def principal(authorization: str | None = Header(default=None)):
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(401, 'authentication required')
        token = authorization[7:]
        role = token_role(token, auth)
        if role and (role['role'] == 'gateway' or local_auth):
            if role['role'] == 'gateway' and role['device_id'] not in trust.get('devices', {}):
                raise HTTPException(403, 'gateway not enrolled')
            return role
        if os.getenv('GOOGLE_CLIENT_ID'):
            try:
                from google.oauth2 import id_token
                from google.auth.transport.requests import Request as GoogleRequest
                def check():
                    import requests
                    class BoundedSession(requests.Session):
                        def request(self, *args, **kwargs):
                            kwargs.setdefault('timeout', 8)
                            return super().request(*args, **kwargs)
                    return id_token.verify_oauth2_token(token, GoogleRequest(session=BoundedSession()), os.environ['GOOGLE_CLIENT_ID'])
                claims = await asyncio.wait_for(asyncio.to_thread(check), timeout=10)
                if claims.get('email_verified') and claims.get('email', '').lower() in {x.strip().lower() for x in os.getenv('COORDINATOR_EMAILS', '').split(',') if x.strip()}:
                    return {'role': 'coordinator', 'actor': claims['email']}
            except Exception:
                pass
        raise HTTPException(401, 'invalid credentials')

    async def coordinator(p=Depends(principal)):
        if p['role'] != 'coordinator':
            raise HTTPException(403, 'coordinator required')
        return p

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'synthetic_only': True, 'store': type(store).__name__, 'inference_provider': 'Google Gemini (configured)' if os.getenv('GOOGLE_CLOUD_PROJECT') else 'unavailable — no GCP project/ADC', 'model': os.getenv('GEMINI_MODEL', 'gemini-3.8-flash'), 'google_client_id': os.getenv('GOOGLE_CLIENT_ID', ''), 'local_auth': local_auth, 'mission_id': MISSION}

    @app.get('/api/incidents')
    def list_incidents():
        state = store.read()
        return {'incidents': service.incidents(state), 'locations': LOCATIONS, 'assignments': state['assignments'], 'receipts': state['receipts'], 'server_time': service.now()}

    @app.get('/api/incidents/{iid}')
    def incident(iid: str):
        item = next((g for g in service.incidents(store.read()) if g['id'] == iid), None)
        if not item:
            raise HTTPException(404, 'incident not found')
        return item

    @app.post('/api/sync')
    def sync(batch: SyncBatch, p=Depends(principal)):
        if p['role'] != 'gateway':
            raise HTTPException(403, 'gateway credentials required')
        try:
            verified = [verify(e, trust) for e in batch.events]
            return store.mutate(lambda s: service.ingest(s, verified, [e.model_dump() for e in batch.events], p['device_id']))
        except Exception as e:
            raise HTTPException(422, 'invalid event batch: '+str(e)[:200]) from e

    @app.post('/api/incidents/{iid}/reassess')
    async def reassess(iid: str, p=Depends(coordinator)):
        item = await asyncio.to_thread(incident, iid)
        if not item['evidence']:
            raise HTTPException(409, 'no evidence yet')
        try:
            assessment, model = await ai.reassess(item['evidence'])
            return await asyncio.to_thread(store.mutate, lambda s: service.save_proposal(s, iid, item['evidence_revision'], assessment, 'Google Gemini', model))
        except ValueError as e:
            raise HTTPException(409, str(e)) from e
        except Exception as e:
            # No inference fallback. Do not leak credentials or raw SDK errors to public clients.
            raise HTTPException(503, 'Gemini inference unavailable or timed out; evidence retained. Check project, model access and ADC.') from e

    @app.post('/api/proposals/{pid}/approve')
    def approve(pid: str, body: Approve, p=Depends(coordinator)):
        try:
            return store.mutate(lambda s: service.approve(s, pid, body.evidence_revision, p.get('actor', 'local-coordinator')))
        except KeyError as e:
            raise HTTPException(404, str(e)) from e
        except ValueError as e:
            raise HTTPException(409, str(e)) from e

    dist = Path(__file__).resolve().parents[1] / 'static'
    if not dist.exists():
        dist = Path(__file__).resolve().parents[2] / 'web/dist'
    if dist.exists():
        app.mount('/assets', StaticFiles(directory=dist/'assets'), name='assets')
        @app.get('/')
        def dashboard():
            return FileResponse(dist/'index.html')
    return app

app = create_app()
