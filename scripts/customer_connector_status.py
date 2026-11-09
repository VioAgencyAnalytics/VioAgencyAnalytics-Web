"""Read-only local operator checklist. Never prints application secrets or grants."""
import json
from pathlib import Path
import sys


def main():
    web=Path(__file__).resolve().parents[1]
    sys.path.insert(0,str(web.parent/'VioAgencyAnalytics-Admin'))
    from kdh.customer_connectors import IMPLEMENTED
    from kdh.customer_integrations import catalogue
    from kdh.customer_provider_adapters import provider_config
    config=json.loads((web/'.work/customer-dev/config.json').read_text(encoding='utf-8'))
    print('Vio application configuration only; this does not prove vendor approval or a live sync.')
    for platform in catalogue()['platforms']:
        spec=provider_config(config,platform['id'])
        print(platform['name']+': '+('APP CONFIGURED' if spec['configured'] else 'VIO APP SETUP PENDING'))
    print('\nExact callback addresses:')
    for provider in ('google','meta','tiktok'):
        print(provider+': '+config['CUSTOMER_WEB_ORIGIN']+'/auth/customer/providers/'+provider+'/callback')
    print('\nGuide: docs/CUSTOMER_CONNECTORS_SETUP_VI.md')


if __name__=='__main__':
    main()
