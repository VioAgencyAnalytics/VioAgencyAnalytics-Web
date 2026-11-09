"""Prepare loopback-only HTTPS; never copy application secrets into TLS files.

Run with the Admin virtualenv (cryptography is an existing dependency).
Trust is limited to a self-signed server certificate, not a signing CA.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from customer_docker import prepare

ORIGIN = 'https://localhost:8444'
ROOT = Path(__file__).resolve().parents[1]
PRIVATE = ROOT / '.work' / 'customer-dev'


def prepare_certificate(private=PRIVATE):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

    tls = private / 'tls'
    tls.mkdir(parents=True, exist_ok=True)
    certificate, keyfile = tls / 'certificate.pem', tls / 'private-key.pem'
    current = datetime.now(timezone.utc)
    if certificate.exists() or keyfile.exists():
        if not certificate.is_file() or not keyfile.is_file():
            raise SystemExit('Incomplete local TLS files; existing files were not overwritten.')
        cert = x509.load_pem_x509_certificate(certificate.read_bytes())
        key = serialization.load_pem_private_key(keyfile.read_bytes(), password=None)
        cert.verify_directly_issued_by(cert)
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        usage = cert.extensions.get_extension_for_class(x509.KeyUsage).value
        eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        if (cert.subject != cert.issuer or cert.not_valid_before_utc > current
                or cert.not_valid_after_utc < current + timedelta(days=7)
                or cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
                or len(san) != 1 or san.get_values_for_type(x509.DNSName) != ['localhost']
                or usage.key_cert_sign or usage.crl_sign
                or list(eku) != [ExtendedKeyUsageOID.SERVER_AUTH]
                or cert.public_key().public_numbers() != key.public_key().public_numbers()):
            raise SystemExit('Existing local TLS certificate needs explicit renewal; no files were replaced.')
    else:
        key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'VioAgencyAnalytics localhost')])
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(current - timedelta(minutes=5))
            .not_valid_after(current + timedelta(days=90))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False,
                key_encipherment=True, data_encipherment=False, key_agreement=False,
                key_cert_sign=False, crl_sign=False, encipher_only=None, decipher_only=None), critical=True)
            .sign(key, hashes.SHA256()))
        with keyfile.open('xb') as target:
            target.write(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                           serialization.NoEncryption()))
        certificate.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    print('Local server certificate ready; localhost only; signing CA disabled; expires ' +
          cert.not_valid_after_utc.date().isoformat() + '.')
    return certificate


def trust_current_user(certificate):
    if os.name != 'nt':
        raise SystemExit('This trust command is for the current Windows user only.')
    result = subprocess.run(['certutil.exe', '-user', '-addstore', '-f', 'Root', str(certificate)],
                            capture_output=True)
    if result.returncode:
        raise SystemExit('Windows could not trust the local server certificate; no application config changed.')
    print('Trusted the localhost server certificate for the current Windows user only.')


def activate_configuration(private=PRIVATE):
    """Stage/validate all env files, back up, then change only the Web origin."""
    values = json.loads((private / 'config.json').read_text(encoding='utf-8'))
    if values.get('CUSTOMER_WEB_ORIGIN') not in ('http://127.0.0.1:8084', ORIGIN):
        raise SystemExit('Expected the existing local configuration; public origin was not overwritten.')
    updated = {**values, 'CUSTOMER_WEB_ORIGIN': ORIGIN}
    names = ('config.json', 'docker-admin.env', 'docker-web.env', 'docker-postgres.env')
    with tempfile.TemporaryDirectory(prefix='https-stage-', dir=private) as folder:
        stage = Path(folder)
        (stage / 'config.json').write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')
        prepare(stage)
        backup = private / 'https-backup' / datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
        backup.mkdir(parents=True, exist_ok=False)
        for name in names:
            if (private / name).is_file():
                shutil.copy2(private / name, backup / name)
        for name in names:
            (stage / name).replace(private / name)
    print('Saved local HTTPS origin; application/SMTP/Google/Meta/DB credentials retained. Private backup created.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trust-current-user', action='store_true')
    parser.add_argument('--activate', action='store_true',
                        help='Use only after registering the HTTPS Meta and Google callbacks.')
    args = parser.parse_args()
    if subprocess.run(['git', 'check-ignore', '-q', str(PRIVATE / 'tls/private-key.pem')], cwd=ROOT).returncode:
        raise SystemExit('TLS directory must be Git ignored; no key was generated.')
    certificate = prepare_certificate()
    if args.trust_current_user:
        trust_current_user(certificate)
    if args.activate:
        activate_configuration()
    print('Web: ' + ORIGIN + '/workspace/login')
    print('Meta callback: ' + ORIGIN + '/auth/customer/providers/meta/callback')
    print('Google callback: ' + ORIGIN + '/auth/customer/google/callback')
    print('Start with: docker compose -f compose.customer.yaml -f compose.customer.https.yaml up -d --no-deps customer-admin web')


if __name__ == '__main__':
    main()
