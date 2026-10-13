"""Paired visual fixture from the existing design data. QA only, never a fallback.

Both original pages and the Bundle adapter receive these same saved numbers.
The mock ReportService is imported only by this explicit local fixture server.
"""
from app.services.reports import ReportService
from app.mappers.dashboard import SPECS
from tests.bundle_fixtures import published_bundle


def paired_fixture():
    service = ReportService()
    originals = {'overview': service.get_overview(), 'seo': service.get_seo(),
        'facebook_ads': service.get_facebook_ads(), 'facebook_content': service.get_facebook_content(),
        'tiktok': service.get_video('tiktok'), 'youtube': service.get_video('youtube')}
    bundle = published_bundle()
    bundle['report'].update(id='rpt_' + 'b' * 32, name='Fixture đối chiếu thiết kế')
    bundle['client']['name'] = 'KinderHealth (Nhi khoa & Tiêm chủng)'
    bundle['comparison'] = {'start':'2026-08-02', 'end':'2026-08-31'}
    bundle['quality'] = {'status':'complete', 'warnings':[]}
    bundle['navigation'] = {'default_section':'overview', 'sections':[*originals, 'gmb']}
    bundle['sections'] = {}
    for index, (channel, original) in enumerate(originals.items()):
        metrics = original['metrics']
        if isinstance(metrics, dict):
            keys = ['total_posts','reach','engagement','engagement_rate','followers_new','link_clicks']
            metrics = [{'value':metrics[key], 'unit':'%' if key=='engagement_rate' else ''} for key in keys]
        sources = {}
        for spec, metric in zip(SPECS[channel], metrics):
            key, label = spec[:2]
            source = sources.setdefault(key.split('.')[0], {'status':'ready', 'label':key.split('.')[0], 'kpis':[]})
            unit = metric.get('unit', '')
            if channel == 'facebook_ads':
                unit = '₫' if key.endswith(('.spend','.cpl')) else '%' if key.endswith('_rate') else ''
            # Preserve fixture units explicitly; production never infers currency.
            if key.endswith('watch_time_minutes'):
                value, unit = metric['value'] * 60, 'minutes'
            elif key.endswith('average_view_duration'):
                minutes, seconds = map(int, metric['value'].split(':'))
                value, unit = minutes * 60 + seconds, 'seconds'
            else:
                value = metric['value']
            source['kpis'].append({'key':key,'label':label,'value':value,'unit':unit})
        base = sources[next(iter(sources))]
        if channel == 'overview':
            base['charts'] = [{'title':key,'type':'line','labels':chart['dates'], 'values':chart['values'],
                'unit':'₫' if key=='spend' else 'count'} for key, chart in original['charts']['trends'].items()]
        elif channel == 'seo':
            base['charts'] = [{'title':'Lượt click tự nhiên','type':'line', **original['data']['series']}]
            sources['keywords']['rows'] = [{**r, 'url':r['landing'], 'previous_position':r['previous']} for r in original['keywords']]
            sources['ga4']['pages'] = [{**r,'pagePath':r['url'],'activeUsers':r['users']} for r in original['landings']]
        elif channel == 'facebook_ads':
            base['campaigns'] = [{k:v for k,v in r.items() if k != 'display'} for r in original['campaigns']]
        elif channel == 'facebook_content':
            base['posts'] = [{**r, 'engagement_rate':str(r['er'])+'%'} for r in original['posts']]
        elif channel in ('tiktok','youtube'):
            chart = original['chart']
            base['charts'] = [{'title':label,'type':'line','labels':chart['dates'],'values':values,
                'unit':'₫' if channel=='tiktok' and i==0 else 'count'}
                for i,(label,values) in enumerate(zip(chart['labels'],chart['series']))]
            base['rows'] = [{**r, 'campaign_name':r['title']} if channel=='tiktok' else
                {**r,'average_view_duration':r['duration'],'subscribers_gained':r['subscribers'],'ctr':str(r['ctr'])+'%'}
                for r in original['rows']]
        bundle['sections'][channel] = {'report_type':channel,'valid':True,'position':index,
            'quality':{'status':'complete','warnings':[]}, 'data':{'demo':True,
                'params':{'start':'2026-09-01','end':'2026-09-30','previous_start':'2026-08-02','previous_end':'2026-08-31'},
                'sources':sources}}
    bundle['sections']['gmb'] = {'report_type':'gmb','valid':True,'data':{}}
    return originals, bundle
