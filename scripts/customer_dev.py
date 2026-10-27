"""Isolated local customer stack. Run init with Admin Python, then admin/web separately.

No existing .env, databases, containers or reporting services are modified.
Generated secrets live only in .work/customer-dev/config.json (Git ignored).
"""
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import getpass
import re
import smtplib
import ssl
from email.message import EmailMessage

WEB = Path(__file__).resolve().parents[1]
ADMIN = WEB.parent / 'VioAgencyAnalytics-Admin'
PRIVATE = WEB / '.work' / 'customer-dev'
CONFIG = PRIVATE / 'config.json'
CONTAINER = 'vio-customer-postgres-dev'


def smtp_address(value):
    value = value.strip()
    if not re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+', value):
        raise SystemExit('Địa chỉ email không hợp lệ. Nhập email thuần, không kèm tên hiển thị.')
    return value


def smtp_connection(values, message=None):
    """Check STARTTLS/auth; send only when explicitly called with a test message."""
    try:
        with smtplib.SMTP(values['CUSTOMER_SMTP_HOST'], int(values['CUSTOMER_SMTP_PORT']), timeout=15) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(values['CUSTOMER_SMTP_USERNAME'], values['CUSTOMER_SMTP_PASSWORD'])
            if message is not None:
                smtp.send_message(message)
    except smtplib.SMTPAuthenticationError:
        raise SystemExit('SMTP từ chối đăng nhập. Kiểm tra username và mật khẩu ứng dụng/API SMTP; với Gmail, không dùng mật khẩu đăng nhập Google.') from None
    except smtplib.SMTPRecipientsRefused:
        raise SystemExit('SMTP từ chối người nhận. Kiểm tra địa chỉ email hoặc giới hạn tài khoản gửi.') from None
    except (OSError, smtplib.SMTPException, ValueError):
        # Server responses can contain account details; never print raw exceptions.
        raise SystemExit('Không thể hoàn tất yêu cầu SMTP. Kiểm tra host, cổng STARTTLS, quyền gửi và kết nối mạng.') from None


def configure_smtp(values):
    print('Cấu hình SMTP STARTTLS (thường dùng cổng 587). Chưa gửi email ở bước này.')
    host = input('SMTP host [smtp.gmail.com]: ').strip() or 'smtp.gmail.com'
    if not re.fullmatch(r'[a-zA-Z0-9.-]+', host):
        raise SystemExit('SMTP host chỉ chứa tên máy chủ, không có https:// hoặc đường dẫn.')
    port_text = input('SMTP STARTTLS port [587]: ').strip() or '587'
    if not port_text.isdigit() or not 1 <= int(port_text) <= 65535 or int(port_text) == 465:
        raise SystemExit('Backend dùng STARTTLS, thường là cổng 587. Chưa hỗ trợ implicit TLS cổng 465.')
    username = input('SMTP username (Gmail: địa chỉ email đầy đủ): ').strip()
    if not username or any(c in username for c in '\r\n'):
        raise SystemExit('SMTP username không hợp lệ.')
    sender = smtp_address(input('Email gửi (From): '))
    password = getpass.getpass('SMTP password / App password (nhập ẩn): ')
    if host.lower() == 'smtp.gmail.com':
        password = password.replace(' ', '')
    if not password:
        raise SystemExit('Chưa nhập mật khẩu SMTP. Cấu hình cũ được giữ nguyên.')
    updated = {**values, 'CUSTOMER_SMTP_HOST': host, 'CUSTOMER_SMTP_PORT': int(port_text),
               'CUSTOMER_SMTP_TLS': 'true', 'CUSTOMER_SMTP_USERNAME': username,
               'CUSTOMER_SMTP_PASSWORD': password, 'CUSTOMER_EMAIL_FROM': sender}
    print('Đang kiểm tra kết nối TLS và đăng nhập SMTP...')
    smtp_connection(updated)
    # Save only after successful authentication, preserving Google/DB settings.
    CONFIG.write_text(json.dumps(updated, indent=2), encoding='utf-8')
    print('Đã kiểm tra đăng nhập và lưu SMTP. Chưa gửi email. Khởi động lại customer Admin và Web để áp dụng.')
    print('Chạy customer_dev.py test-smtp để gửi một email thử đến địa chỉ bạn nhập.')


def test_smtp(values):
    required = ('CUSTOMER_SMTP_HOST', 'CUSTOMER_SMTP_PORT', 'CUSTOMER_SMTP_USERNAME',
                'CUSTOMER_SMTP_PASSWORD', 'CUSTOMER_EMAIL_FROM')
    if not all(values.get(key) for key in required):
        raise SystemExit('Chạy configure-smtp trước khi gửi thử.')
    recipient = smtp_address(input('Địa chỉ nhận một email thử SMTP: '))
    message = EmailMessage()
    message['From'], message['To'] = values['CUSTOMER_EMAIL_FROM'], recipient
    message['Subject'] = 'VioAgencyAnalytics — Kiểm tra SMTP'
    message.set_content('Đây là email kiểm tra cấu hình gửi thư của VioAgencyAnalytics.\n'
                        'Email này không chứa mã xác minh hoặc liên kết đặt lại mật khẩu.\n')
    smtp_connection(values, message)
    print('Máy chủ SMTP đã chấp nhận email thử. Kiểm tra Hộp thư đến và Spam của địa chỉ nhận.')


def init():
    from cryptography.fernet import Fernet
    PRIVATE.mkdir(parents=True, exist_ok=True)
    if not CONFIG.exists():
        values = {'CUSTOMER_AUTH_ENABLED':'true', 'CUSTOMER_SERVICE_TOKEN':secrets.token_urlsafe(48),
                  'CUSTOMER_WEB_ORIGIN':'http://127.0.0.1:8084', 'CUSTOMER_BACKEND_URL':'http://127.0.0.1:8094',
                  'CUSTOMER_GOOGLE_CLIENT_ID':'', 'CUSTOMER_GOOGLE_CLIENT_SECRET':'',
                  'CUSTOMER_SMTP_HOST':'', 'CUSTOMER_EMAIL_FROM':'',
                  'ENCRYPTION_KEY':Fernet.generate_key().decode(), 'POSTGRES_PASSWORD':secrets.token_urlsafe(32)}
        values['DATABASE_URL'] = 'postgresql://vio_customer:' + values['POSTGRES_PASSWORD'] + '@127.0.0.1:5434/vio_customer'
        CONFIG.write_text(json.dumps(values, indent=2), encoding='utf-8')
    values = json.loads(CONFIG.read_text(encoding='utf-8'))
    envfile = PRIVATE / 'postgres.env'
    envfile.write_text('POSTGRES_USER=vio_customer\nPOSTGRES_DB=vio_customer\nPOSTGRES_PASSWORD=' + values['POSTGRES_PASSWORD'] + '\n', encoding='utf-8')
    existing = subprocess.run(['docker','inspect','--format','{{index .Config.Labels "vio.customer.dev"}}',CONTAINER], capture_output=True, text=True)
    if existing.returncode == 0:
        if existing.stdout.strip() != 'true':
            raise SystemExit('Container name is occupied by a different service; no changes made.')
        subprocess.run(['docker','start',CONTAINER], check=True, stdout=subprocess.DEVNULL)
    else:
        subprocess.run(['docker','run','-d','--name',CONTAINER,'--label','vio.customer.dev=true',
                        '--restart','unless-stopped','-p','127.0.0.1:5434:5432','--env-file',str(envfile),
                        '-v','vio-customer-pg-data:/var/lib/postgresql/data','postgres:16'], check=True, stdout=subprocess.DEVNULL)
    import psycopg
    for _ in range(30):
        try:
            with psycopg.connect(values['DATABASE_URL'], connect_timeout=2) as connection:
                connection.execute('SELECT 1')
            print('Customer PostgreSQL ready on 127.0.0.1:5434; persistent volume vio-customer-pg-data.')
            return
        except psycopg.OperationalError:
            time.sleep(1)
    raise SystemExit('Customer PostgreSQL not ready. Check the dedicated container.')


def run(mode):
    if not CONFIG.exists():
        raise SystemExit('Run init first with the Admin virtual environment.')
    values = json.loads(CONFIG.read_text(encoding='utf-8'))
    os.environ.update({key:str(value) for key,value in values.items() if key != 'POSTGRES_PASSWORD'})
    os.environ.update(APP_ENV='production', DEBUG='false')
    if mode == 'admin':
        os.chdir(ADMIN)
        sys.path.insert(0, str(ADMIN))
        from kdh.app import create_app
        from waitress import serve
        app = create_app({'DATA_DIR':str(ADMIN / 'instance' / 'customer-dev'),
                          'APP_URL':'http://127.0.0.1:8094', 'COOKIE_SECURE':False,
                          'INITIAL_ADMIN_EMAIL':'', 'INITIAL_ADMIN_PASSWORD':'',
                          'GOOGLE_CLIENT_ID':'', 'GOOGLE_CLIENT_SECRET':'', 'JOB_MODE':'worker'})
        print('Customer Admin API: http://127.0.0.1:8094', flush=True)
        serve(app, host='127.0.0.1', port=8094, threads=8)
    elif mode == 'web':
        os.chdir(WEB)
        sys.path.insert(0, str(WEB))
        import uvicorn
        # Do not log OAuth authorization codes or trust arbitrary forwarding headers.
        uvicorn.run('main:app', host='127.0.0.1', port=8084, access_log=False, proxy_headers=False)
    elif mode == 'test-admin':
        os.chdir(ADMIN)
        os.environ['TEST_DATABASE_URL'] = values['DATABASE_URL']
        # Tests own provider fixtures and disposable DBs, never the dev runtime DB.
        os.environ.update(CUSTOMER_AUTH_ENABLED='false', DATABASE_URL='', ENCRYPTION_KEY='',
                          META_CLIENT_ID='client_kinderhealth', META_APP_ID='', META_APP_SECRET='',
                          META_CONFIG_ID='', GOOGLE_CLIENT_ID='', GOOGLE_CLIENT_SECRET='',
                          INITIAL_ADMIN_EMAIL='', INITIAL_ADMIN_PASSWORD='')
        raise SystemExit(subprocess.call([str(ADMIN / '.venv' / 'Scripts' / 'python.exe'), '-m','unittest','discover','-s','tests','-v']))
    elif mode == 'configure-google':
        client_id = input('Google OAuth Client ID: ').strip()
        client_secret = getpass.getpass('Google OAuth Client Secret (input is hidden): ').strip()
        if not client_id.endswith('.apps.googleusercontent.com') or len(client_secret) < 16:
            raise SystemExit('Client ID hoặc Client Secret không đúng định dạng. Không có thay đổi nào được lưu.')
        values['CUSTOMER_GOOGLE_CLIENT_ID'] = client_id
        values['CUSTOMER_GOOGLE_CLIENT_SECRET'] = client_secret
        CONFIG.write_text(json.dumps(values, indent=2), encoding='utf-8')
        print('Đã lưu cấu hình Google trong .work/customer-dev/config.json. Khởi động lại customer Admin và Web để áp dụng.')
    elif mode == 'configure-smtp':
        configure_smtp(values)
    elif mode == 'test-smtp':
        test_smtp(values)
    else:
        raise SystemExit('Expected init, admin, web, test-admin, configure-google, configure-smtp or test-smtp.')


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) == 2 else ''
    init() if mode == 'init' else run(mode)
