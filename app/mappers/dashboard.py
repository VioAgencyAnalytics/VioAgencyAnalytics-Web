"""Bind saved Bundle values to the existing channel dashboard components.

Only formatting and row selection happen here. No totals/rates/claims are derived.
"""
from dataclasses import asdict
from urllib.parse import urlencode

from app.schemas.bundle_view import BundleView, MetricView, QualityView, SectionView

TEMPLATES = {'overview': 'overview', 'seo': 'seo', 'facebook_ads': 'facebook_ads',
             'facebook_content': 'facebook_content', 'tiktok': 'tiktok', 'youtube': 'youtube'}
ALIASES = {'facebook-ads': 'facebook_ads', 'facebook-content': 'facebook_content', 'tiktok-ads': 'tiktok'}
SPECS = {
    'seo': [('gsc.impressions', 'Tổng lượt hiển thị (Impressions)', 'visibility', 'impressions'),
            ('gsc.clicks', 'Lượt click tự nhiên (Clicks)', 'ads_click', 'clicks'),
            ('ga4.organic_users', 'Organic Users', 'group', 'organic_users'),
            ('keywords.top10', 'Từ khóa Top 10', 'trending_up', 'top10'),
            ('seo.leads', 'Leads từ SEO', 'patient_list', 'seo_leads'),
            ('seo.conversion_rate', 'Tỷ lệ chuyển đổi (CR)', 'percent', 'seo_conversion_rate')],
    'overview': [('marketing.reach', 'Tổng lượt tiếp cận', 'hub', 'marketing_reach'),
                 ('marketing.traffic', 'Lượt truy cập Website', 'language', 'marketing_traffic'),
                 ('marketing.engagement', 'Tổng lượt tương tác', 'thumb_up', 'marketing_engagement'),
                 ('marketing.leads', 'Khách hàng tiềm năng', 'contact_page', 'marketing_leads'),
                 ('marketing.spend', 'Tổng chi phí quảng cáo', 'payments', 'marketing_spend')],
    'facebook_ads': [('facebook_ads.' + key, label, icon, key) for key, label, icon in (
        ('spend', 'Tổng Chi tiêu', 'payments'), ('reach', 'Lượt Tiếp Cận', 'visibility'),
        ('link_clicks', 'Click Liên Kết', 'ads_click'), ('leads', 'Leads Thành Công', 'person_add'),
        ('cpl', 'Chi Phí / Lead (CPL)', 'trending_down'), ('lead_conversion_rate', 'Tỷ Lệ Chuyển Đổi', 'percent'))],
    'facebook_content': [('facebook_content.' + key, label, icon, key) for key, label, icon in (
        ('posts_published', 'Tổng bài đăng', 'article'), ('reach', 'Lượt tiếp cận', 'visibility'),
        ('engagements', 'Tổng tương tác', 'thumb_up'), ('engagement_rate', 'Tỷ lệ tương tác (ER)', 'monitoring'),
        ('followers_gained', 'Followers mới', 'group_add'), ('link_clicks', 'Click liên kết', 'ads_click'))],
    'tiktok': [('tiktok_ads.' + key, label, icon, key) for key, label, icon in (
        ('spend', 'Tổng chi tiêu (Spend)', 'payments'), ('reach', 'Lượt tiếp cận (Reach)', 'visibility'),
        ('clicks', 'Lượt click & CTR', 'ads_click'), ('video_views', 'Lượt xem video & 6s', 'play_circle'),
        ('leads', 'Khách hàng tiềm năng', 'group_add'), ('cost_per_lead', 'Chi phí / Lead (CPA)', 'trending_down'))],
    'youtube': [('youtube.' + key, label, icon, key) for key, label, icon in (
        ('views', 'Lượt xem', 'visibility'), ('watch_time_minutes', 'Thời gian xem', 'schedule'),
        ('subscribers_gained', 'Subscribers mới', 'group_add'), ('impressions', 'Lượt hiển thị', 'monitoring'),
        ('impressions_ctr', 'CTR Thumbnail', 'ads_click'), ('average_view_duration', 'Thời lượng xem TB', 'timelapse'))],
}


def display(value, unit=''):
    if value is None:
        return 'Chưa có dữ liệu'
    if type(value) in (int, float):
        # Ratios are only converted for display; saved values remain untouched.
        if unit in ('ratio', 'tỷ lệ (0–1)'):
            return f'{value * 100:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.') + '%'
        precision = 0 if unit in ('VND', '₫') else 2 if unit in ('currency', 'USD', 'EUR', '%', 'percent') else 4
        result = f'{value:,.{precision}f}'
        if precision:
            result = result.rstrip('0').rstrip('.')
        result = result.replace(',', '_').replace('.', ',').replace('_', '.')
        return result + ('%' if unit in ('percent', '%') else '')
    return str(value)


def metric_cards(section, channel):
    result = []
    for key, label, icon, alias in SPECS.get(channel, []):
        matched = [m for m in section.metrics if m.key == key]
        if not matched:
            matched = [m for m in section.metrics if m.key == alias and m.source_key == key.split('.')[0]]
        metric = matched[0] if len(matched) == 1 else MetricView(key, label)
        result.append({**asdict(metric), 'label': label, 'icon': icon, 'text': display(metric.value, metric.unit),
                       'unit_text': '' if metric.unit in ('ratio', 'tỷ lệ (0–1)', 'percent', '%') else {'count':'', 'currency':'tiền tệ (chưa có mã)', 'minutes':'phút', 'seconds':'giây'}.get(metric.unit, metric.unit),
                       'previous_text': display(metric.previous, metric.unit)})
    return result


def dashboard_context(bundle, selected, path, preview=False):
    section = next(s for s in bundle.sections if s.key == selected)
    channel = ALIASES.get(selected, selected)
    view = asdict(section)
    view.update(channel=channel, kpis=metric_cards(section, channel), preview=preview)
    view['channel_cards'] = [{**asdict(s), 'kpis': metric_cards(s, ALIASES.get(s.key, s.key)),
        'icon': {'seo':'search_insights','facebook_content':'thumb_up','facebook_ads':'campaign',
                 'tiktok':'play_circle','youtube':'smart_display','gmb':'storefront'}.get(s.key, 'monitoring')}
        for s in bundle.sections if s.key != 'overview']
    view['all_metrics'] = [{**asdict(m), 'text': display(m.value, m.unit)} for m in section.metrics]
    # Only exact saved metrics may occupy a funnel step. Never join audiences
    # across providers or derive an attribution/conversion rate here.
    by_key = {}
    for metric in view['all_metrics']:
        key = metric['key'] if '.' in metric['key'] else metric['source_key'] + '.' + metric['key']
        by_key.setdefault(key, []).append(metric)
    view['saved_metrics'] = {key: items[0] for key, items in by_key.items() if len(items) == 1}
    view['keyword_tables'], view['landing_tables'], view['other_tables'] = [], [], []
    view['campaign_rows'] = []
    for table in view['tables']:
        keys = {c['key'] for c in table['columns']}
        if 'keyword' in keys:
            view['keyword_tables'].append(table)
        elif 'pagePath' in keys or 'landingPage' in keys:
            view['landing_tables'].append(table)
        else:
            view['other_tables'].append(table)
        if channel == 'facebook_ads' and (
            'campaign_name' in keys or 'name' in keys
        ):
            for row in table['rows']:
                units = {c['key']: c.get('unit', '') for c in table['columns']}
                view['campaign_rows'].append([{'value': next((row[k]['value'] for k in aliases if k in row), None),
                    'text': next((display(row[k]['value'], units.get(k, '')) + (' ' + units[k] if units.get(k) not in ('', None, 'count', 'ratio', 'percent', '%') else '') for k in aliases if k in row), 'Chưa có dữ liệu')} for aliases in (
                    ('campaign_name', 'name'), ('objective',), ('spend',), ('reach',), ('clicks',), ('leads',), ('cpl',), ('assessment',))])
    # Keep designed table columns even when no row exists. Never join sources or
    # infer keyword rank from traffic; missing cells remain null.
    keyword_columns = [('keyword','Từ khóa'),('url','Trang đích'),('previous_position','Vị trí cũ'),
        ('position','Vị trí mới'),('change','Thay đổi'),('clicks','Lượt click'),('impressions','Hiển thị'),('ctr','CTR')]
    landing_columns = [('pagePath','Trang đích (URL)'),('activeUsers','Users'),('clicks','Clicks'),('leads','Leads'),('cr','CR')]
    def shaped(tables, title, columns):
        chosen = tables or [{'title':title, 'source':'Snapshot Admin', 'rows':[], 'columns':[]}]
        result = []
        for table in chosen:
            units = {c['key']:c.get('unit','') for c in table['columns']}
            result.append({**table, 'columns':[{'key':key,'label':label,'unit':units.get(key,'')} for key,label in columns],
                'rows':[{key:row.get(key, {'value':None,'url':None}) for key,_ in columns} for row in table['rows']]})
        return result
    view['keyword_tables'] = shaped(view['keyword_tables'], 'Thứ hạng từ khóa', keyword_columns)
    view['landing_tables'] = shaped(view['landing_tables'], 'Hiệu quả trang đích', landing_columns)
    columns = {
        'facebook_content': [('title','Bài viết / Tiêu đề'),('date','Ngày đăng'),('format','Loại nội dung'),('reach','Reach'),('engagement','Engagement'),('engagement_rate','ER'),('comments','Comments'),('shares','Shares'),('clicks','Clicks')],
        'tiktok': [('campaign_name','Tên chiến dịch / Mã'),('spend','Chi tiêu'),('reach','Reach'),('views','Views'),('clicks','Clicks'),('leads','Leads'),('cpa','CPA'),('status','Trạng thái')],
        'youtube': [('title','Video / Tiêu đề'),('date','Ngày đăng'),('views','Lượt xem'),('average_view_duration','Thời gian xem TB'),('ctr','CTR Thumbnail'),('subscribers_gained','Subscribers mới')],
    }
    if channel in columns:
        keys = {'facebook_content':{'title','post_id'}, 'tiktok':{'campaign_name','campaign_id'}, 'youtube':{'title','video_id'}}[channel]
        view['detail_tables'] = shaped([t for t in view['tables'] if {c['key'] for c in t['columns']} & keys], 'Chi tiết ' + section.label, columns[channel])
    links = {ALIASES.get(s.key, s.key).replace('_', '-'): path + '?' + urlencode({'revision': bundle.revision, 'section': s.key})
             for s in bundle.sections}
    view['links'] = links
    return {'bundle': asdict(bundle), 'dashboard': view, 'active_report': channel.replace('_', '-'),
            'selected_section': selected, 'snapshot_links': links, 'snapshot_home': links.get('overview', next(iter(links.values()), path)),
            'title': section.label, 'snapshot_format': display, 'video': {'channel': channel},
            'snapshot_template': 'pages/' + TEMPLATES.get(channel, 'snapshot') + '/index.html'}


def preview_dashboard(candidate, issues, candidate_id):
    """Internal preview stays distinct: never fabricate a published Bundle."""
    from app.mappers.bundle import BundleViewMapper
    raw = candidate['marketing']['preview']
    period = raw.get('period') or {k: candidate.get('params', {}).get(k, '') for k in ('start', 'end')}
    source_keys = set(candidate.get('sources', {})) | {w.get('metric_id', '').split('.')[0]
        for w in raw.get('widgets', []) if isinstance(w, dict)}
    channels = {'seo' if key in ('ga4', 'gsc', 'keywords', 'seo') else
                'tiktok' if key == 'tiktok_ads' else key for key in source_keys if key}
    channel = next(iter(channels)) if len(channels) == 1 else 'overview'
    from app.mappers.bundle import SECTION_NAMES
    section = SectionView(channel, channel, SECTION_NAMES.get(channel, channel), channel, period, None, 'partial',
                          QualityView('partial', list(issues)))
    mapper = BundleViewMapper()
    for source, data in candidate.get('sources', {}).items():
        if isinstance(data, dict):
            mapper._source(section, source, data, False)
    section.metrics = [MetricView(w.get('metric_id', ''), w.get('label', w.get('metric_id', '')), w.get('value'),
        w.get('unit', ''), (w.get('comparison') or {}).get('previous_value'), None, w.get('source', ''),
        available=w.get('value') is not None, source_key=w.get('metric_id', '').split('.')[0])
        for w in raw.get('widgets', []) if isinstance(w, dict)]
    return BundleView(candidate_id, 0, 'draft', 'Xem trước nội bộ', 'KinderHealth', period,
        raw.get('comparison'), candidate.get('created_at'), None, section.quality, [section], channel)
