"""Loopback bridge to the private Customer Admin Compose service.

Only loopback 8094 is bound; the destination is fixed, never browser supplied.
This keeps the BFF's loopback-only HTTP policy and the existing OAuth origin.
No Google, SMTP or database credentials are required in this container.
"""
import asyncio

import uvicorn


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
    bridge = await asyncio.start_server(relay, '127.0.0.1', 8094)
    async with bridge:
        await uvicorn.Server(uvicorn.Config(
            'main:app', host='0.0.0.0', port=8000,
            access_log=False, proxy_headers=False)).serve()


if __name__ == '__main__':
    asyncio.run(main())
