"""Logo DTO boundary. Only small raster images may be served on the Web origin."""
import base64
import binascii
import re

from fastapi.responses import Response

from app.customer_auth import CustomerError, HEADERS, backend, error_response

MAX_IMAGE = 128 * 1024
MAGIC = {'image/png':(b'\x89PNG\r\n\x1a\n',), 'image/jpeg':(b'\xff\xd8\xff',),
         'image/gif':(b'GIF87a',b'GIF89a'), 'image/x-icon':(b'\x00\x00\x01\x00',)}


def image_payload(payload):
    if payload.get('available') is not True:
        return None
    kind, encoded = payload.get('content_type'), payload.get('content')
    try:
        if kind not in MAGIC or not isinstance(encoded,str) or len(encoded) > (MAX_IMAGE + 2) // 3 * 4:
            raise ValueError()
        data = base64.b64decode(encoded, validate=True)
        if not data or len(data) > MAX_IMAGE or not data.startswith(MAGIC[kind]):
            raise ValueError()
    except (ValueError, binascii.Error):
        raise CustomerError(502, 'Chưa thể tải logo website.') from None
    return kind, data


def preview_result(payload):
    image = image_payload(payload)
    if image is None:
        return {'available':False}
    kind, data = image
    return {'available':True,'image':'data:' + kind + ';base64,' + base64.b64encode(data).decode('ascii')}


async def read(request, workspace_id):
    try:
        if not re.fullmatch(r'[a-f0-9]{32}', workspace_id):
            raise CustomerError(404, 'Không tìm thấy Workspace.')
        image = image_payload(await backend(request, 'GET', '/workspaces/' + workspace_id + '/logo'))
        if image is None:
            return Response(status_code=204, headers=HEADERS)
        kind, data = image
        return Response(data, media_type=kind, headers={**HEADERS,
            'Cross-Origin-Resource-Policy':'same-origin','Content-Security-Policy':"default-src 'none'; sandbox"})
    except CustomerError as exc:
        return error_response(exc)
