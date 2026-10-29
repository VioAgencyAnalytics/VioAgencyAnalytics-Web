"""Empty customer Dashboard contract. Admin owns analytics and source authorization."""
from copy import deepcopy

from app.mappers.customer_overview import build_overview


def build_marketing(details, catalogue):
    view = build_overview(details, catalogue)
    view.pop('reports')
    view.pop('channels')
    view['trends']['impressions'] = {'status': 'empty', 'points': []}
    groups = {'paid': 'Quảng cáo trả phí', 'search': 'Tìm kiếm & Website', 'content': 'Nội dung & Xã hội'}
    view['groups'] = [{'id': key, 'label': label} for key, label in groups.items()]
    view['platforms'] = deepcopy(catalogue.get('platforms', []))
    for platform in view['platforms']:
        platform['group'] = ('paid' if 'ads' in platform['categories'] else
                             'search' if platform['id'] in ('ga4', 'gsc', 'business_profile') else 'content')
    view['platform_metrics'] = []
    view['campaigns'] = []
    return view
