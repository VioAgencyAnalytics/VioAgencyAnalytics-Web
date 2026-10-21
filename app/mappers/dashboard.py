"""Bind saved Bundle values to the existing channel dashboard components.

Only formatting and row selection happen here. No totals/rates/claims are derived.
"""
from dataclasses import asdict
from datetime import datetime
import re
from urllib.parse import urlencode

from app.schemas.bundle_view import BundleView, MetricView, QualityView, SectionView

TEMPLATES = {'overview': 'overview', 'seo': 'seo', 'facebook_ads': 'facebook_ads',
             'facebook_content': 'facebook_content', 'tiktok': 'tiktok', 'youtube': 'youtube'}
ALIASES = {'facebook-ads': 'facebook_ads', 'facebook-content': 'facebook_content', 'tiktok-ads': 'tiktok'}
KEYWORD_TIERS = (5, 10, 20, 30, 50, 100)
SPECS = {
    'seo': [('gsc.impressions', 'Lượt hiển thị', 'visibility', 'impressions'),
            ('gsc.clicks', 'Lượt nhấp tìm kiếm', 'ads_click', 'clicks'),
            ('ga4.organic_users', 'Organic Users', 'group', 'organic_users'),
            ('keywords.top10', 'Từ khóa Top 10', 'trending_up', 'top10'),
            ('seo.leads', 'Leads từ SEO', 'patient_list', 'seo_leads'),
            ('seo.conversion_rate', 'Tỷ lệ chuyển đổi', 'percent', 'seo_conversion_rate')],
    'overview': [('marketing.reach', 'Tổng lượt tiếp cận', 'hub', 'marketing_reach'),
                 ('marketing.traffic', 'Lượt truy cập Website', 'language', 'marketing_traffic'),
                 ('marketing.engagement', 'Tổng lượt tương tác', 'thumb_up', 'marketing_engagement'),
                 ('marketing.leads', 'Khách hàng tiềm năng', 'contact_page', 'marketing_leads'),
                 ('marketing.spend', 'Tổng chi phí quảng cáo', 'payments', 'marketing_spend')],
    'facebook_ads': [('facebook_ads.' + key, label, icon, key) for key, label, icon in (
        ('spend', 'Tổng chi tiêu', 'payments'), ('reach', 'Lượt tiếp cận', 'visibility'),
        ('link_clicks', 'Lượt nhấp liên kết', 'ads_click'), ('leads', 'Leads', 'person_add'),
        ('cpl', 'Chi phí / lead', 'trending_down'), ('lead_conversion_rate', 'Tỷ lệ chuyển đổi', 'percent'))],
    'facebook_content': [('facebook_content.' + key, label, icon, key) for key, label, icon in (
        ('posts_published', 'Tổng bài đăng', 'article'), ('reach', 'Lượt tiếp cận', 'visibility'),
        ('engagements', 'Tổng tương tác', 'thumb_up'), ('engagement_rate', 'Tỷ lệ tương tác (ER)', 'monitoring'),
        ('followers_gained', 'Người theo dõi mới', 'group_add'), ('link_clicks', 'Lượt nhấp liên kết', 'ads_click'))],
    'tiktok': [('tiktok_ads.' + key, label, icon, key) for key, label, icon in (
        ('spend', 'Tổng chi tiêu', 'payments'), ('reach', 'Lượt tiếp cận', 'visibility'),
        ('clicks', 'Lượt nhấp', 'ads_click'), ('video_views', 'Lượt xem video', 'play_circle'),
        ('leads', 'Khách hàng tiềm năng', 'group_add'), ('cost_per_lead', 'Chi phí / lead', 'trending_down'))],
    'youtube': [('youtube.' + key, label, icon, key) for key, label, icon in (
        ('views', 'Lượt xem', 'visibility'), ('watch_time_minutes', 'Thời gian xem', 'schedule'),
        ('subscribers_gained', 'Người đăng ký mới', 'group_add'), ('impressions', 'Lượt hiển thị', 'monitoring'),
        ('impressions_ctr', 'CTR hình thu nhỏ', 'ads_click'), ('average_view_duration', 'Thời lượng xem TB', 'timelapse'))],
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
        matched = [m for m in section.metrics if m.key == key or
                   (m.key == alias and m.source_key == key.split('.')[0])]
        metric = matched[0] if len(matched) == 1 else MetricView(key, label)
        result.append({**asdict(metric), 'label': label, 'icon': icon, 'text': display(metric.value, metric.unit),
                       'unit_text': '' if metric.unit in ('ratio', 'tỷ lệ (0–1)', 'percent', '%') else {'count':'', 'currency':'tiền tệ (chưa có mã)', 'minutes':'phút', 'seconds':'giây'}.get(metric.unit, metric.unit),
                       'previous_text': display(metric.previous, metric.unit)})
    return result


def content_cards(section, lifetime=False):
    keys = ('reactions_lifetime', 'comments_lifetime', 'shares_lifetime') if lifetime else ('posts_published', 'engagements')
    cards = []
    for key in keys:
        matches = [m for m in section.metrics if m.key == 'facebook_content.' + key]
        if len(matches) != 1:
            continue
        metric = matches[0]
        cards.append({**asdict(metric), 'icon': 'thumb_up' if lifetime else 'article',
                      'text': display(metric.value, metric.unit), 'unit_text': '', 'previous_text': '—'})
    return cards


def content_presentation(bundle, section, view):
    """Format saved values and deterministic scope notes; never derive performance."""
    cards = content_cards(section) + content_cards(section, lifetime=True)
    order = ['posts_published', 'reactions_lifetime', 'comments_lifetime', 'engagements', 'shares_lifetime']
    by_key = {c['key'].split('.')[-1]: c for c in cards}
    icons = dict(zip(order, ['article', 'thumb_up', 'chat_bubble', 'monitoring', 'share']))
    view['overview_kpis'] = [dict(by_key[k], icon=icons[k]) for k in order if k in by_key]
    name = bundle.name.split('|')[0].strip()
    # This prefix is report naming metadata, not a client or Facebook Page name.
    view['report_display_name'] = name.removeprefix('KDH – ').removeprefix('KDH — ')
    view['snapshot_time'] = section.fetched_at or 'Chưa có thời điểm chốt'
    if section.fetched_at:
        try:
            stamp = datetime.fromisoformat(section.fetched_at.replace('Z', '+00:00'))
            if stamp.utcoffset() is not None and stamp.utcoffset().total_seconds() == 0:
                view['snapshot_time'] = stamp.strftime('%d/%m/%Y %H:%M:%S UTC')
        except ValueError:
            pass
    view['content_charts'] = [dict(c, title='Bài đăng theo ngày', unit='bài', integer_axis=True, kind='bar',
                                    timezone=section.timezone) if c['title'] == 'posts_published theo ngày' else c
                              for c in view['charts']]
    preferred = [('post_id', 'Mã bài đăng'), ('date', 'Ngày đăng (UTC)' if section.timezone == 'UTC' else 'Ngày nguồn'),
                 ('reactions_lifetime', 'Cảm xúc'), ('comments_lifetime', 'Bình luận'),
                 ('shares_lifetime', 'Chia sẻ')]
    view['detail_tables'] = []
    view['post_links'] = {}
    page_id = section.source_identity.get('external_id', '')
    for table in view['tables']:
        keys = {c['key'] for c in table['columns']}
        if 'post_id' not in keys:
            continue
        columns = [dict(key=k, label=label, unit='') for k, label in preferred if k in keys]
        view['detail_tables'].append(dict(table, title='Danh sách bài đăng', columns=columns, metadata=True))
        # Navigation only: retain the immutable rows and metric values verbatim.
        for row in table['rows']:
            post_id = row.get('post_id', {}).get('value')
            match = re.fullmatch(r'([1-9][0-9]{0,31})_([1-9][0-9]{0,31})', post_id) if isinstance(post_id, str) else None
            if section.source_identity.get('asset_type') == 'facebook_page' and match and match[1] == page_id:
                view['post_links'][post_id] = 'https://www.facebook.com/permalink.php?' + urlencode({'story_fbid': match[2], 'id': page_id})
    notes = {key: {'facts': [], 'quality': [], 'approved': []} for key in
             ('overview', 'publishing', 'posts', 'lifetime', 'formats', 'topics', 'reach', 'insights')}
    def coverage(metric):
        c = metric['coverage']
        return f"{c['available']}/{c['expected']} " + ('bài' if c['unit'] == 'posts' else 'ngày') if c else 'chưa có độ phủ'
    posts = by_key.get('posts_published')
    if posts and posts['value'] is not None:
        notes['overview']['facts'].append(f"Trong kỳ ghi nhận {posts['text']} bài đăng. Độ phủ dữ liệu số bài đăng: {coverage(posts)}.")
    engagements = by_key.get('engagements')
    if engagements and engagements['value'] is None:
        notes['overview']['quality'].append(f"Tương tác phát sinh trong kỳ chưa có dữ liệu ({engagements['status']}; {coverage(engagements)}). Giá trị thiếu không phải 0.")
    notes['publishing']['quality'].append(f"Ngày theo múi giờ nguồn {section.timezone or 'chưa được cung cấp'}. Biểu đồ dùng các điểm đã lưu; lọc ngày không thay đổi KPI toàn kỳ.")
    for metric in view['lifetime_kpis']:
        if metric['value'] is not None:
            notes['lifetime']['facts'].append(f"{metric['text']} {metric['label']} tại snapshot {view['snapshot_time']}; độ phủ {coverage(metric)}.")
        else:
            notes['lifetime']['quality'].append(f"{metric['label']}: {metric['status']}, độ phủ {coverage(metric)}; chưa có tổng đã chốt trong Bundle.")
    notes['lifetime']['quality'].append('Bộ đếm lifetime tích lũy đến snapshot, không phải lượng tương tác phát sinh riêng trong kỳ.')
    notes['posts']['quality'].append('Ngày và bộ đếm từng bài được giữ nguyên từ Bundle. Ô chưa có dữ liệu là null; không thay bằng 0. Chọn Post ID để xem metadata đã lưu.')
    view['content_breakdowns'] = {}
    for key, dimensions in [('formats', {'format', 'format_name'}), ('topics', {'topic', 'topic_name'}),
                            ('reach', {'organic_reach', 'paid_reach'})]:
        tables = [t for t in view['tables'] if 'post_id' not in {c['key'] for c in t['columns']}
                  and any(row.get(k, {}).get('value') is not None for row in t['rows'] for k in dimensions)]
        view['content_breakdowns'][key] = tables
        if not tables:
            notes[key]['quality'].append({'formats':'Snapshot chưa có dữ liệu phân bổ định dạng nội dung.',
                'topics':'Snapshot chưa có dữ liệu phân bổ theo chủ đề.',
                'reach':'Snapshot hiện chưa có dữ liệu tiếp cận Organic/Paid, vì vậy chưa thể đánh giá hiệu quả tiếp cận.'}[key])
    # The mapper has already filtered approvals. Associate exact metric labels/keys only.
    for evidence in view['evidence']:
        if not evidence.get('claim'):
            continue  # A verified number alone is not a professional conclusion.
        matched = next((k for k, m in by_key.items() if evidence.get('metric') in (m['key'], m['label'])), None)
        target = 'lifetime' if matched and matched.endswith('_lifetime') else 'overview' if matched else 'insights'
        notes[target]['approved'].append(evidence)
    view['commentary'] = notes
    report = section.content_report
    if report:
        # Copy the exact Admin projection; never reconstruct taxonomy or rates.
        rows = report['sections']['posts']['rows']
        columns = [('title', 'Bài viết'), ('post_id', 'Mã bài đăng'), ('date', 'Ngày đăng (UTC)'),
                   ('format', 'Định dạng'), ('topic', 'Chủ đề'), ('reactions_lifetime', 'Cảm xúc'),
                   ('comments_lifetime', 'Bình luận'), ('shares_lifetime', 'Chia sẻ')]
        view['detail_tables'] = [dict(title='Danh sách bài đăng', source='Facebook Content', metadata=True,
            status=report['sections']['posts']['status'],
            columns=[dict(key=k, label=label, unit='') for k, label in columns],
            rows=[{k: dict(value=r.get(k), url=None) for k, _ in columns} for r in rows])]
        from app.bundle_safety import safe_url
        for row in rows:
            url = safe_url(row.get('permalink_url'))
            if url:
                view['post_links'][row['post_id']] = url
        for key in ('formats', 'topics'):
            item = report['sections'][key]
            view['content_breakdowns'][key] = [] if not item['rows'] else [dict(title=item['label'],
                source='Phân loại biên tập' if key == 'topics' else 'Facebook Content', status=item['status'],
                columns=[dict(key=k, label=label, unit='') for k, label in [('label', 'Nhóm'), ('count', 'Số bài'), ('percent', 'Tỷ trọng (%)')]],
                rows=[{k: dict(value=r.get(k), url=None) for k in ('label', 'count', 'percent')} for r in item['rows']])]
        for key, item in report['sections'].items():
            note = item.get('commentary')
            if note and note.get('status') == 'approved':
                notes['insights']['approved'].append(dict(claim=note['text'], metric=item['label'], origin='editorial'))


def dashboard_context(bundle, selected, path, preview=False):
    section = next(s for s in bundle.sections if s.key == selected)
    channel = ALIASES.get(selected, selected)
    view = asdict(section)
    view.update(channel=channel, kpis=metric_cards(section, channel), preview=preview)
    if channel == 'facebook_content' and section.source_identity:
        view['kpis'] = content_cards(section)
        view['lifetime_kpis'] = content_cards(section, lifetime=True)
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
    view['keyword_tiers'] = [dict(limit=k, key=f'keywords.top{k}',
        metric=view['saved_metrics'].get(f'keywords.top{k}')) for k in KEYWORD_TIERS]
    view['traffic_metrics'] = [m for m in view['all_metrics'] if m['source_key'] in ('ga4', 'gsc')]
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
    keyword_columns = [('keyword','Từ khóa'),('url','Trang đích'),('date','Ngày tracking'),('previous_position','Vị trí kỳ trước'),
        ('position','Vị trí ghi nhận'),('change','Thay đổi'),('clicks','Lượt click'),('impressions','Hiển thị'),('ctr','CTR')]
    landing_columns = [('pagePath','Trang đích (URL)'),('activeUsers','Users'),('clicks','Clicks'),('leads','Leads'),('cr','CR')]
    def shaped(tables, title, columns):
        chosen = tables or [{'title':title, 'source':'Snapshot Admin', 'rows':[], 'columns':[]}]
        result = []
        for table in chosen:
            units = {c['key']:c.get('unit','') for c in table['columns']}
            # Retain additional saved dimensions/metrics instead of dropping their scope.
            shaped_columns = [{'key':key,'label':label,'unit':units.get(key,'')} for key,label in columns]
            if 'landingPage' in units and 'pagePath' not in units:
                shaped_columns[0]['key'] = 'landingPage'
            if channel == 'seo':
                shaped_columns += [c for c in table['columns'] if c['key'] not in {c['key'] for c in shaped_columns}]
            result.append({**table, 'columns':shaped_columns,
                'rows':[{c['key']:row.get(c['key'], {'value':None,'url':None}) for c in shaped_columns} for row in table['rows']]})
        return result
    view['keyword_tables'] = shaped(view['keyword_tables'], 'Thứ hạng từ khóa', keyword_columns)
    view['landing_tables'] = shaped(view['landing_tables'], 'Hiệu quả trang đích', landing_columns)
    columns = {
        'facebook_content': [('title','Bài viết / Tiêu đề'),('date','Ngày đăng'),('format','Loại nội dung'),('reach','Reach'),('engagement','Engagement'),('engagement_rate','ER'),('comments','Comments'),('shares','Shares'),('clicks','Clicks')],
        'tiktok': [('campaign_name','Tên chiến dịch / Mã'),('spend','Chi tiêu'),('reach','Reach'),('views','Views'),('clicks','Clicks'),('leads','Leads'),('cpa','CPA'),('status','Trạng thái')],
        'youtube': [('title','Video / Tiêu đề'),('date','Ngày đăng'),('views','Lượt xem'),('average_view_duration','Thời gian xem TB'),('ctr','CTR hình thu nhỏ'),('subscribers_gained','Người đăng ký mới')],
    }
    if channel in columns:
        keys = {'facebook_content':{'title','post_id'}, 'tiktok':{'campaign_name','campaign_id'}, 'youtube':{'title','video_id'}}[channel]
        view['detail_tables'] = shaped([t for t in view['tables'] if {c['key'] for c in t['columns']} & keys], 'Chi tiết ' + section.label, columns[channel])
    if channel == 'facebook_content' and section.source_identity:
        content_presentation(bundle, section, view)
    if channel == 'facebook_content':
        content_shell(bundle, section, view)
    links = {ALIASES.get(s.key, s.key).replace('_', '-'): path + '?' + urlencode({'revision': bundle.revision, 'section': s.key})
             for s in bundle.sections}
    view['links'] = links
    return {'bundle': asdict(bundle), 'dashboard': view, 'active_report': channel.replace('_', '-'),
            'selected_section': selected, 'snapshot_links': links, 'snapshot_home': links.get('overview', next(iter(links.values()), path)),
            'title': section.label, 'snapshot_format': display, 'video': {'channel': channel},
            'snapshot_template': 'pages/' + TEMPLATES.get(channel, 'snapshot') + '/index.html'}


def content_shell(bundle, section, view):
    """Select visible components only; retain all frozen values in the view model."""
    view['content_live'] = bundle.report_id != 'layout-preview'
    labels = {'reactions_lifetime': 'Cảm xúc tích lũy', 'comments_lifetime': 'Bình luận tích lũy',
              'shares_lifetime': 'Chia sẻ tích lũy'}
    cards = metric_cards(section, 'facebook_content') + content_cards(section, lifetime=True)
    view['visible_content_kpis'] = [dict(m, label=labels.get(m['key'].split('.')[-1], m['label']))
        for m in cards if m['available'] and m['value'] is not None and m['status'] not in ('no_data', 'unavailable')]
    view['visible_content_charts'] = [c for c in view.get('content_charts', view['charts'])
        if c['status'] not in ('no_data', 'unavailable') and any(v is not None for v in c['values'])]
    def populated(tables):
        result = []
        for table in tables:
            if table.get('status') in ('no_data', 'unavailable'):
                continue
            columns = [c for c in table['columns']
                if any(row.get(c['key'], {}).get('value') is not None for row in table['rows'])]
            if columns and table['rows']:
                result.append(dict(table, columns=columns))
        return result
    view['visible_content_tables'] = populated(view['detail_tables'])
    view['visible_content_breakdowns'] = {key: populated(tables)
        for key, tables in view.get('content_breakdowns', {}).items()}
    view['content_approved_notes'] = [item for notes in view.get('commentary', {}).values() for item in notes['approved']]
    view['visible_content_sections'] = ['fc-summary']
    if view['visible_content_charts'] or view['visible_content_breakdowns'].get('formats'):
        view['visible_content_sections'].append('fc-formats')
    if view['visible_content_tables']:
        view['visible_content_sections'].append('fc-posts')
    for key, section_id in [('topics', 'fc-topics'), ('reach', 'fc-reach')]:
        if view['visible_content_breakdowns'].get(key):
            view['visible_content_sections'].append(section_id)
    if view['content_approved_notes'] or view['opportunities']:
        view['visible_content_sections'].append('fc-insights')


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
