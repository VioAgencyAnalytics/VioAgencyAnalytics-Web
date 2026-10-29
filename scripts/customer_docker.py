"""Prepare separate private environments for the local customer Docker stack."""
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def write_env(path, values):
    # Compose single-quoted values preserve dollar/hash characters literally.
    lines = []
    for key, value in values.items():
        value = str(value)
        if any(c in value for c in '\r\n\x00'):
            raise SystemExit('Invalid newline in private configuration; environment not written.')
        value = value.replace("'", "\\'")
        lines.append(f"{key}='{value}'\n")
    path.write_text(''.join(lines), encoding='utf-8')


def prepare(private=None):
    private = private or Path(__file__).resolve().parents[1] / '.work' / 'customer-dev'
    values = json.loads((private / 'config.json').read_text(encoding='utf-8'))
    if values.get('CUSTOMER_WEB_ORIGIN') != 'http://127.0.0.1:8084':
        raise SystemExit('Expected the existing local Customer Web origin on port 8084.')
    token = values.get('CUSTOMER_SERVICE_TOKEN', '')
    if not isinstance(token, str) or len(token) < 32 or any(c in token for c in '\r\n\x00\''):
        raise SystemExit('Invalid Customer service credential; no environment file written.')
    database = urlsplit(values.get('DATABASE_URL', ''))
    if (database.scheme != 'postgresql' or database.hostname not in ('127.0.0.1', 'localhost')
            or database.port != 5434 or database.path != '/vio_customer'
            or database.username != 'vio_customer' or not database.password
            or not values.get('ENCRYPTION_KEY') or not values.get('POSTGRES_PASSWORD')):
        raise SystemExit('Expected the existing isolated customer PostgreSQL configuration.')
    selected = {
        'CUSTOMER_AUTH_ENABLED': 'true',
        'CUSTOMER_BACKEND_URL': 'http://127.0.0.1:8094',
        'CUSTOMER_WEB_ORIGIN': values['CUSTOMER_WEB_ORIGIN'],
        'CUSTOMER_SERVICE_TOKEN': token,
    }
    write_env(private / 'docker-web.env', selected)
    admin_keys = ('CUSTOMER_GOOGLE_CLIENT_ID', 'CUSTOMER_GOOGLE_CLIENT_SECRET',
                  'CUSTOMER_SMTP_HOST', 'CUSTOMER_SMTP_PORT', 'CUSTOMER_SMTP_TLS',
                  'CUSTOMER_SMTP_USERNAME', 'CUSTOMER_SMTP_PASSWORD', 'CUSTOMER_EMAIL_FROM')
    write_env(private / 'docker-admin.env', {
        **{key: values[key] for key in admin_keys if key in values},
        'CUSTOMER_AUTH_ENABLED': 'true', 'CUSTOMER_WEB_ORIGIN': values['CUSTOMER_WEB_ORIGIN'],
        'CUSTOMER_SERVICE_TOKEN': token, 'ENCRYPTION_KEY': values['ENCRYPTION_KEY'],
        'DATABASE_URL': urlunsplit(database._replace(
            netloc=database.netloc.rsplit('@', 1)[0] + '@customer-postgres:5432')),
    })
    write_env(private / 'docker-postgres.env', {
        'POSTGRES_USER': 'vio_customer', 'POSTGRES_DB': 'vio_customer',
        'POSTGRES_PASSWORD': values['POSTGRES_PASSWORD'],
    })
    print('Prepared separate ignored Web/Admin/PostgreSQL env files. Web has no provider/SMTP/DB secrets.')


if __name__ == '__main__':
    prepare()
