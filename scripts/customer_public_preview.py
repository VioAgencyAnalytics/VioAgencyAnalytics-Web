"""Stage an isolated public-preview configuration; never deploy or modify grants."""
import argparse
import json
from pathlib import Path
import tempfile

from customer_docker import prepare, public_origin


def stage(origin, private=None):
    origin = public_origin(origin)
    private = private or Path(__file__).resolve().parents[1]/'.work/customer-dev'
    original = (private/'config.json').read_bytes()
    values = json.loads(original)
    destination = private/'public-preview'
    destination.mkdir(exist_ok=True)
    # Keep live local env files and provider credentials unchanged until the
    # provider owner has registered the exact public callbacks.
    with tempfile.TemporaryDirectory(prefix='staged-', dir=destination) as folder:
        staged = Path(folder)
        (staged/'config.json').write_text(json.dumps({**values, 'CUSTOMER_WEB_ORIGIN': origin}), encoding='utf-8')
        prepare(staged, allow_public=True)
        for name in ('config.json', 'docker-web.env', 'docker-admin.env', 'docker-postgres.env'):
            (staged/name).replace(destination/name)
    callbacks = {key: origin+path for key,path in {
        'google_signin':'/auth/customer/google/callback',
        'google_data':'/auth/customer/providers/google/callback',
        'meta':'/auth/customer/providers/meta/callback'}.items()}
    result = {'status':'STAGED_ONLY', 'origin':origin, 'callbacks':callbacks,
              'callbacks_registered':False, 'runtime_changed':False,
              'grant_transition_review_required':True}
    (destination/'readiness.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    assert (private/'config.json').read_bytes() == original
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('origin')
    stage(parser.parse_args().origin)
