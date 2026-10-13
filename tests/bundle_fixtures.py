"""Synthetic contract fixtures only; never real client metrics or credentials."""
from copy import deepcopy

REPORT_ID = 'rpt_fixture_only'
SERVICE_TOKEN = 'fixture-backend-secret-not-a-real-token'
PREVIEW_USER = 'fixture-viewer'
PREVIEW_PASSWORD = 'fixture-preview-password-for-tests-only'


def published_bundle():
    data = {
        'schema_version': '1.0',
        'report': {'id': REPORT_ID, 'revision': 2, 'status': 'provisional', 'name': 'Báo cáo kiểm thử renderer'},
        'client': {'id': 'fixture-client', 'name': 'Khách hàng kiểm thử'},
        'period': {'start':'2026-09-01', 'end':'2026-09-30'},
        'comparison': {'start':'2026-08-01','end':'2026-08-31'},
        'freshness': {'generated_at':'2026-10-01T01:00:00Z','published_at':'2026-10-01T02:00:00Z'},
        'quality': {'status':'partial','warnings':['Cảnh báo chất lượng fixture']},
        'navigation': {'default_section':'seo','sections':['seo','overview']}, 'branding': {},
        'sections': {
            'seo': {'dataset_id':'fixture-dataset','report_type':'seo','valid':True,'position':0,
                    'created_at':'2026-10-01T00:00:00Z','quality':{'status':'partial','warnings':[]},
                    'data':{'params':{'start':'2026-09-01','end':'2026-09-30','demo':True,
                                      'previous_start':'2026-08-01','previous_end':'2026-08-31'},
                            'sources':{'ga4':{'label':'GA4 fixture','status':'ready','latest_available_date':'2026-09-29',
                                              'totals':{'sessions':123,'activeUsers':None,'screenPageViews':0},
                                              'previous':{'sessions':100},
                                              'daily':[{'date':'2026-09-01','sessions':2},{'date':'2026-09-02','sessions':None},{'date':'2026-09-03','sessions':3}],
                                              'channels':[{'sessionDefaultChannelGroup':'Organic Search','sessions':7}],
                                              'pages':[], 'warnings':['Thiếu một ngày trong fixture']}}}},
            'overview': {'report_type':'ga4','valid':True,'position':1,'quality':{'status':'unknown','warnings':[]},'data':{}},
            'not-published': {'report_type':'ga4','valid':True,'data':{'totals':{'hiddenMetric':987654321}}},
        },
    }
    return deepcopy(data)
