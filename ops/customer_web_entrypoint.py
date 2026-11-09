"""Loopback bridge to the private Customer Admin Compose service.

Only loopback 8094 is bound; the destination is fixed, never browser supplied.
This keeps the BFF's loopback-only HTTP policy and the existing OAuth origin.
No Google, SMTP or database credentials are required in this container.
"""
import asyncio
import os
from pathlib import Path
from urllib.parse import quote

import uvicorn


LOCAL_HTTPS_ORIGIN = 'https://localhost:8444'


def tls_settings(environ=None):
    """Local TLS is opt-in and fails closed if its certificate is incomplete."""
    env = os.environ if environ is None else environ
    cert, key = env.get('CUSTOMER_LOCAL_TLS_CERT', ''), env.get('CUSTOMER_LOCAL_TLS_KEY', '')
    if not cert and not key:
        return None
    if (not cert or not key or env.get('CUSTOMER_WEB_ORIGIN') != LOCAL_HTTPS_ORIGIN
            or not Path(cert).is_file() or not Path(key).is_file()):
        raise RuntimeError('Local HTTPS configuration is incomplete; no HTTP fallback is allowed.')
    return {'ssl_certfile': cert, 'ssl_keyfile': key}


async def local_https_redirect(scope, receive, send):
    """Old loopback bookmarks redirect; credentials/callbacks never use HTTP."""
    if scope['type'] != 'http':
        return
    hosts = [value for key, value in scope.get('headers', []) if key.lower() == b'host']
    allowed = (b'127.0.0.1:8084', b'localhost:8084')
    path = scope.get('path', '/')
    headers = [(b'cache-control', b'no-store'), (b'referrer-policy', b'no-referrer'),
               (b'x-content-type-options', b'nosniff')]
    status, body = 400, b'Open the configured local HTTPS website.'
    if len(hosts) == 1 and hosts[0] in allowed:
        if scope['method'] not in ('GET', 'HEAD') or path.startswith(('/api/', '/auth/')):
            status, body = 426, b'Use HTTPS for account requests. Open https://localhost:8444/workspace/login'
        else:
            # The destination is fixed, never derived from Host/Forwarded headers.
            # Do not propagate OAuth codes/state or arbitrary query strings.
            destination = LOCAL_HTTPS_ORIGIN + quote(path, safe='/')
            headers.append((b'location', destination.encode('ascii')))
            status, body = 307, b''
    await send({'type': 'http.response.start', 'status': status, 'headers': headers})
    await send({'type': 'http.response.body', 'body': b'' if scope['method'] == 'HEAD' else body})


async def relay(reader, writer):
    upstream = None
    try:
        remote_reader, upstream = await asyncio.wait_for(
            asyncio.open_connection('customer-admin', 8094), timeout=5)

        async def copy(source, destination):
            while data := await asyncio.wait_for(source.read(65536), timeout=60):
                destination.write(data)
                await destination.drain()
            if destination.can_write_eof():
                destination.write_eof()

        await asyncio.gather(copy(reader, upstream), copy(remote_reader, writer))
    except (OSError, asyncio.TimeoutError):
        pass  # BFF returns its existing safe upstream-unavailable response.
    finally:
        for stream in (writer, upstream):
            if stream is not None:
                stream.close()


async def main():
    tls = tls_settings()
    bridge = await asyncio.start_server(relay, '127.0.0.1', 8094)
    async with bridge:
        if not tls:
            await uvicorn.Server(uvicorn.Config(
                'main:app', host='0.0.0.0', port=8000,
                access_log=False, proxy_headers=False)).serve()
            return
        # TLS terminates in the Web container. No proxy header trust is needed.
        servers = [
            uvicorn.Server(uvicorn.Config('main:app', host='0.0.0.0', port=8443,
                access_log=False, proxy_headers=False, **tls)),
            uvicorn.Server(uvicorn.Config(local_https_redirect, host='0.0.0.0', port=8000,
                access_log=False, proxy_headers=False, lifespan='off')),
        ]
        tasks = [asyncio.create_task(server.serve()) for server in servers]
        try:
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for server in servers:
                server.should_exit = True
            await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(main())
