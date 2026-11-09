"""Configure provider APP credentials only; never ask for customer access tokens."""
import argparse
import getpass
import json
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import parse_qs, urlsplit

from customer_docker import prepare


def primary_meta_application():
    """Read only application settings; never inspect an encrypted user grant."""
    result = subprocess.run(['docker','inspect','VioAgencyAnaltics-Admin'],capture_output=True,text=True,encoding='utf-8')
    try:
        if result.returncode:
            raise ValueError()
        container=json.loads(result.stdout)[0]
        labels=container['Config']['Labels']
        if labels.get('com.docker.compose.project')!='vioagencyanaltics-admin' or labels.get('com.docker.compose.service')!='admin':
            raise ValueError()
        values=dict(item.split('=',1) for item in container['Config']['Env'])
        return {key:values.get('META_'+key,'') for key in ('APP_ID','APP_SECRET','CONFIG_ID','GRAPH_VERSION')}
    except (KeyError,TypeError,ValueError,IndexError):
        raise SystemExit('Cannot read the existing Primary Meta application. No configuration changed.') from None


def save_configuration(private, values):
    # Validate and generate all environments before replacing any live file.
    with tempfile.TemporaryDirectory(prefix='provider-prepare-',dir=private) as folder:
        staged=Path(folder)
        (staged/'config.json').write_text(json.dumps(values,ensure_ascii=False,indent=2),encoding='utf-8')
        prepare(staged)
        for name in ('config.json','docker-admin.env','docker-web.env','docker-postgres.env'):
            (staged/name).replace(private/name)


def configure(provider, private=None, meta_source='both', reuse_primary=False, reuse_signin=False):
    private = private or Path(__file__).resolve().parents[1]/'.work'/'customer-dev'
    path = private/'config.json'
    if not path.exists():
        raise SystemExit('Run customer_dev.py init before configuring provider applications.')
    values = json.loads(path.read_text(encoding='utf-8'))
    updates = {}
    if (provider not in ('google','google-ads','meta','tiktok') or meta_source not in ('content','ads','instagram','both')
            or (reuse_primary and (provider!='meta' or meta_source=='instagram')) or (reuse_signin and provider!='google')):
        raise SystemExit('Invalid provider source. No configuration changed.')
    def ask(key, label, secret=False):
        full = 'CUSTOMER_DATA_'+key
        entered = (getpass.getpass(label+' (hidden; blank keeps existing): ') if secret else input(label+' (blank keeps existing): ')).strip()
        value = entered or values.get(full,'')
        if not value or any(c in value for c in '\r\n\x00'):
            raise SystemExit('Invalid or missing value. No configuration changed.')
        updates[full]=value
        return value
    if provider=='google':
        if reuse_signin:
            client,secret=values.get('CUSTOMER_GOOGLE_CLIENT_ID',''),values.get('CUSTOMER_GOOGLE_CLIENT_SECRET','')
            updates={'CUSTOMER_DATA_GOOGLE_CLIENT_ID':client,'CUSTOMER_DATA_GOOGLE_CLIENT_SECRET':secret}
            if any(values.get(key) and values[key]!=value for key,value in updates.items()):
                raise SystemExit('Google Data already uses a different application. No configuration changed.')
        else:
            client=ask('GOOGLE_CLIENT_ID','Google Data OAuth Client ID')
            secret=ask('GOOGLE_CLIENT_SECRET','Google Data OAuth Client Secret',True)
        if not client.endswith('.apps.googleusercontent.com') or len(secret)<16:
            raise SystemExit('Invalid Google client. No configuration changed.')
    elif provider=='google-ads':
        if not values.get('CUSTOMER_DATA_GOOGLE_CLIENT_ID') or not values.get('CUSTOMER_DATA_GOOGLE_CLIENT_SECRET'):
            raise SystemExit('Configure the Google Data application first. No configuration changed.')
        updates['CUSTOMER_DATA_GOOGLE_ADS_VERSION']='v26'
    elif provider=='tiktok':
        app=ask('TIKTOK_APP_ID','TikTok for Business App ID')
        secret=ask('TIKTOK_APP_SECRET','TikTok for Business App Secret',True)
        address=ask('TIKTOK_AUTHORIZATION_URL','Advertiser authorization URL from the app portal')
        parts=urlsplit(address);query=parse_qs(parts.query,keep_blank_values=True)
        expected=values['CUSTOMER_WEB_ORIGIN']+'/auth/customer/providers/tiktok/callback'
        if (not re.fullmatch(r'\d+',app) or len(secret)<16 or parts.scheme!='https'
                or parts.netloc!='business-api.tiktok.com' or parts.path not in ('/portal/auth','/portal/auth/')
                or parts.fragment or set(query)-{'app_id','redirect_uri','state'}
                or any(len(items)!=1 for items in query.values())
                or query.get('app_id')!=[app] or query.get('redirect_uri')!=[expected]):
            raise SystemExit('Invalid app-generated TikTok advertiser URL or callback. No configuration changed.')
    else:
        sources=('content','ads') if meta_source=='both' else (meta_source,)
        if reuse_primary:
            existing=primary_meta_application()
            app,secret,graph=existing['APP_ID'],existing['APP_SECRET'],existing['GRAPH_VERSION']
            updates={'CUSTOMER_DATA_META_APP_ID':app,'CUSTOMER_DATA_META_APP_SECRET':secret,'CUSTOMER_DATA_META_GRAPH_VERSION':graph,
                     **{'CUSTOMER_DATA_META_'+source.upper()+'_CONFIG_ID':existing['CONFIG_ID'] for source in sources}}
            if any(values.get(key) and values[key]!=value for key,value in updates.items()):
                raise SystemExit('Customer app already differs. Use interactive configuration to change it deliberately.')
            config_ids=[existing['CONFIG_ID']]
        else:
            app=ask('META_APP_ID','Meta App ID')
            secret=ask('META_APP_SECRET','Meta App Secret',True)
            config_ids=[ask('META_'+source.upper()+'_CONFIG_ID','Facebook Login for Business '+source+' config ID') for source in sources]
            graph=ask('META_GRAPH_VERSION','Graph API version, for example v26.0')
        if (not all(isinstance(v,str) and re.fullmatch(r'\d+',v) for v in (app,*config_ids))
                or not isinstance(secret,str) or len(secret)<16 or any(c in secret for c in '\r\n\x00')
                or not isinstance(graph,str) or not re.fullmatch(r'v\d+\.\d+',graph)):
            raise SystemExit('Invalid Meta application. No configuration changed.')
    save_configuration(private,{**values,**updates})
    print('Saved backend-only provider application configuration; no customer grant or email was created.')
    print('Register exact redirect URI: '+values['CUSTOMER_WEB_ORIGIN']+'/auth/customer/providers/'+('google' if provider=='google-ads' else provider)+'/callback')
    print('Restart customer-admin; customers then authorize their own accounts from Customer Web.')
    if provider=='meta':
        print('Meta source(s): '+meta_source+'. Register the callback in the existing app and verify USER token permissions.')
        print('App dashboard: https://developers.facebook.com/apps/'+app+'/')
    if provider=='google-ads':
        print('Enable Google Ads API in the OAuth client Cloud project and request production access there.')
        print('Google sunset developer tokens on 2026-09-09; no developer token is needed for this connector.')
        print('Cloud project access: https://console.cloud.google.com/google-ads-api/overview')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('provider',choices=('google','google-ads','meta','tiktok'))
    parser.add_argument('--meta-source',choices=('content','ads','instagram','both'),default='both')
    parser.add_argument('--reuse-primary-meta-app',action='store_true',help='Copy only existing Primary APP settings; no customer tokens or data.')
    parser.add_argument('--reuse-signin-google-app',action='store_true',help='Use the same Vio Google APP, with separate data consent and grants. Never copies a sign-in token.')
    args=parser.parse_args()
    configure(args.provider,meta_source=args.meta_source,reuse_primary=args.reuse_primary_meta_app,reuse_signin=args.reuse_signin_google_app)
