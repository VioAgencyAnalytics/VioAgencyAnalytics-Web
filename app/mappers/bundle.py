"""Contract 1.0 adapter: copy saved values; never derive totals, rates or claims."""
from datetime import date, timedelta
from typing import Any

from app.bundle_safety import check_safe_payload, safe_url
from app.repositories.admin_bundle import AdminBundleContractError
from app.schemas.bundle_view import (
    BundleView, ChartView, EvidenceCard, MetricView, OpportunityCard,
    QualityView, SectionView, SourceView, TableView,
)

SECTION_NAMES = {
    'overview': 'Tổng quan Marketing', 'seo': 'SEO & Lưu lượng Website',
    'facebook-ads': 'Facebook Ads', 'facebook-content': 'Facebook Content',
    'tiktok': 'TikTok Ads', 'youtube': 'YouTube', 'gmb': 'Google Business Profile',
    'ga4': 'Google Analytics 4', 'gsc': 'Google Search Console', 'keywords': 'Thứ hạng từ khóa',
    'google-ads': 'Google Ads', 'instagram-organic': 'Instagram Organic',
    'tiktok-organic': 'TikTok Organic', 'leads': 'Leads', 'crm': 'CRM', 'revenue': 'Doanh thu',
}
SECTION_NAMES.update({'google_ads': 'Google Ads', 'facebook_ads': 'Facebook Ads',
    'facebook_content': 'Facebook Content', 'instagram': 'Instagram Organic',
    'tiktok_ads': 'TikTok Ads', 'tiktok_organic': 'TikTok Organic'})
SUPPORTED = set(SECTION_NAMES) | {'facebook-content-30d', 'facebook-content-6m', 'tiktok-ads', 'google-business-profile', 'marketing-overview', 'keyword-ranking'}
LABELS = {
    'activeUsers': 'Người dùng hoạt động', 'sessions': 'Phiên truy cập', 'screenPageViews': 'Lượt xem trang',
    'engagementRate': 'Tỷ lệ tương tác', 'clicks': 'Lượt nhấp', 'impressions': 'Lượt hiển thị',
    'ctr': 'CTR', 'position': 'Vị trí', 'top5': 'Top 5', 'top10': 'Top 10', 'top20': 'Top 20',
    'top30': 'Top 30', 'top50': 'Top 50', 'top100': 'Top 100',
    'views': 'Lượt xem', 'calls': 'Cuộc gọi', 'directions': 'Lượt chỉ đường', 'website_clicks': 'Nhấp website',
    'date': 'Ngày', 'query': 'Truy vấn', 'keyword': 'Từ khóa', 'url': 'URL nguồn', 'location': 'Mã cơ sở',
    'name': 'Tên', 'sessionDefaultChannelGroup': 'Kênh', 'pagePath': 'Trang', 'spend': 'Chi tiêu',
    'reach': 'Tiếp cận', 'leads': 'Leads', 'revenue': 'Doanh thu',
}
DETAIL_LISTS = {'daily': 'Theo ngày', 'channels': 'Nguồn truy cập', 'pages': 'Trang', 'queries': 'Truy vấn',
                'entries': 'Bản ghi', 'rows': 'Chi tiết', 'campaigns': 'Chiến dịch', 'posts': 'Bài đăng', 'videos': 'Video'}


def fail(message: str) -> None:
    raise AdminBundleContractError(message)


def text(value: object) -> str | None:
    return value if isinstance(value, str) and value.strip() else None


def scalar(value: object) -> str | int | float | None:
    return value if type(value) in (str, int, float) else None


def number(value: object) -> bool:
    return type(value) in (int, float)


def notes(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def period(value: object) -> dict[str, str]:
    if not isinstance(value, dict):
        fail('Kỳ báo cáo không đúng cấu trúc.')
    try:
        start, end = value['start'], value['end']
        if date.fromisoformat(start).isoformat() != start or date.fromisoformat(end).isoformat() != end or start > end:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        fail('Kỳ báo cáo không hợp lệ.')
    return {'start': start, 'end': end}


def quality(value: object) -> QualityView:
    if not isinstance(value, dict):
        return QualityView(warnings=['Chưa có metadata chất lượng.'])
    status = value.get('status')
    warnings = notes(value.get('warnings'))
    if status not in ('complete', 'partial', 'failed', 'unknown'):
        warnings.append('Trạng thái chất lượng chưa được hỗ trợ; chưa thể xác minh.')
        status = 'unknown'
    return QualityView(status, warnings, text(value.get('latest_available_date')))


def demo(value: object) -> bool:
    if isinstance(value, dict):
        if any(value.get(key) is True for key in ('demo', 'mock', 'is_demo', 'is_mock')):
            return True
        if any(isinstance(value.get(key), str) and value[key].lower() in ('demo', 'mock', 'sample', 'simulated') for key in ('source', 'data_source', 'origin', 'mode', 'provenance')):
            return True
        return any(demo(item) for item in value.values())
    if isinstance(value, list):
        return any(demo(item) for item in value)
    return False


def metric_unit(source: str, key: str, explicit: object = None) -> str:
    if isinstance(explicit, str):
        return explicit
    # Google contract stores these as fractions. Preserve raw values and label their unit.
    if (source == 'gsc' and key == 'ctr') or (source == 'ga4' and key == 'engagementRate'):
        return 'tỷ lệ (0–1)'
    return ''


class BundleViewMapper:
    def map(self, payload: dict[str, Any], expected_report_id: str, expected_revision: int | None = None) -> BundleView:
        check_safe_payload(payload)
        if not isinstance(payload, dict) or payload.get('schema_version') != '1.0':
            fail('Chỉ hỗ trợ schema_version 1.0.')
        for key in ('report', 'client', 'period', 'freshness', 'quality', 'navigation', 'branding', 'sections'):
            if not isinstance(payload.get(key), dict):
                fail('Bundle thiếu object bắt buộc: ' + key)
        if 'comparison' not in payload:
            fail('Bundle thiếu comparison.')
        report, nav = payload['report'], payload['navigation']
        if report.get('id') != expected_report_id or report.get('status') not in ('provisional', 'final'):
            fail('Report ID hoặc trạng thái xuất bản không hợp lệ.')
        revision = report.get('revision')
        if type(revision) is not int or revision <= 0 or (expected_revision is not None and revision != expected_revision):
            fail('Revision không khớp hoặc không hợp lệ.')
        keys = nav.get('sections')
        if not isinstance(keys, list) or any(not isinstance(k, str) or not k for k in keys) or len(set(keys)) != len(keys):
            fail('navigation.sections phải là danh sách section key duy nhất có thứ tự.')
        report_period = period(payload['period'])
        comparison = period(payload['comparison']) if payload['comparison'] is not None else None
        overall = quality(payload['quality'])
        sections = []
        for key in keys:
            if key not in payload['sections']:
                overall.warnings.append('Navigation tham chiếu section không có snapshot; mục đó được ẩn.')
                continue
            sections.append(self._section(key, payload['sections'][key], report_period, comparison, payload['client'].get('id'), len(sections)))
        default = nav.get('default_section')
        if default not in [s.key for s in sections]:
            default = sections[0].key if sections else None
            overall.warnings.append('Trang mặc định không có snapshot; chọn mục đầu tiên hiện có.')
        provenance = ('demo' if demo(payload) or any('DEMO' in note.upper() for note in overall.warnings) else
                      'provider_origin_confirmed' if sections and all(s.provenance == 'provider_origin_confirmed' for s in sections) else 'unverified')
        if provenance != 'demo' and any(section.provenance == 'demo' for section in sections):
            provenance = 'demo'
        return BundleView(expected_report_id, revision, report['status'], text(report.get('name')) or expected_report_id,
                          text(payload['client'].get('name')) or 'Chưa có tên khách hàng', report_period, comparison,
                          text(payload['freshness'].get('generated_at')), text(payload['freshness'].get('published_at')),
                          overall, sections, default, provenance, text(payload['branding'].get('name')))

    def _section(self, key: str, raw: object, report_period: dict, comparison: dict | None, client_id: object, index: int) -> SectionView:
        if not isinstance(raw, dict):
            fail('Section không phải object.')
        q = quality(raw.get('quality'))
        view = SectionView(key, f'bundle-section-{index}', SECTION_NAMES.get(key.replace('_', '-'), key),
                           text(raw.get('report_type')), report_period.copy(), raw.get('valid') if type(raw.get('valid')) is bool else None,
                           'empty', q, text(raw.get('dataset_id')), text(raw.get('created_at')))
        if 'position' in raw and raw['position'] != index:
            q.warnings.append('Position khác thứ tự navigation; hiển thị theo navigation đã xuất bản.')
        if view.valid is False:
            q.warnings.append('Dataset được Admin đánh dấu không hợp lệ; số liệu nếu có chỉ là dữ liệu một phần.')
        data = raw.get('data')
        if data is None:
            return view
        if not isinstance(data, dict):
            fail('Section data không phải object.')
        released = data.get('dataset_kind') == 'marketing_release_snapshot_v1'
        if released:
            release = data.get('release', {})
            if (not isinstance(release, dict) or release.get('schema_version') != '1.0'
                    or release.get('state') != 'release_approved' or release.get('provider_origin_confirmed') is not True
                    or not text(release.get('approval_id')) or not text(release.get('seal'))
                    or not isinstance(release.get('checks'), list) or not release['checks']
                    or any(not isinstance(c, dict) or c.get('status') != 'provider_origin_confirmed' or c.get('issues') for c in release['checks'])
                    or demo(data)):
                fail('Bản phát hành thiếu bằng chứng xác minh/phê duyệt của Admin.')
        elif 'marketing' in data or str(data.get('dataset_kind', '')).startswith('marketing_'):
            fail('Dataset Marketing nội bộ không được dùng trong báo cáo khách hàng.')
        params = data.get('params') if isinstance(data.get('params'), dict) else {}
        for owner in (data.get('client_id'), params.get('client_id')):
            if owner is not None and owner != client_id:
                fail('Dataset không khớp khách hàng của bundle.')
        view.provenance = 'demo' if demo(data) or any('DEMO' in note.upper() for note in q.warnings) else 'unverified'
        if released and view.provenance != 'demo':
            view.provenance = 'provider_origin_confirmed'
        if params.get('start') is not None or params.get('end') is not None:
            if params.get('start') != report_period['start'] or params.get('end') != report_period['end']:
                view.state = 'unavailable'
                q.warnings.append('Kỳ dataset không khớp kỳ báo cáo. Nội dung được khóa để tránh trình bày sai kỳ.')
                return view
        compare_ok = comparison is not None
        if comparison and (params.get('compare') is False or any(params.get(k) != comparison[v] for k, v in (('previous_start', 'start'), ('previous_end', 'end')))):
            compare_ok = False
            q.warnings.append('Chưa xác minh được kỳ so sánh của dataset; không hiển thị số kỳ trước hoặc thay đổi.')
        if data and view.report_type and view.report_type.replace('_', '-') not in SUPPORTED:
            view.state = 'unsupported'
            q.warnings.append('Loại báo cáo này chưa có adapter được hỗ trợ.')
            return view
        sources = data.get('sources', {})
        if not isinstance(sources, dict):
            fail('Dataset sources không phải object.')
        if any(k in data for k in ('totals', 'kpis', 'daily', 'charts', 'tables')):
            self._source(view, view.report_type or key, data, compare_ok)
        for source_key, source in sources.items():
            if not isinstance(source, dict):
                q.warnings.append('Một nguồn trong snapshot sai cấu trúc; không được hiển thị.')
                continue
            self._source(view, str(source_key), source, compare_ok)
        view.evidence = self._evidence(data.get('evidence'), released)
        view.opportunities = self._opportunities(data.get('opportunities'), released)
        if released:
            marketing = data.get('marketing')
            if not isinstance(marketing, dict) or marketing.get('kind') != 'approved_release':
                fail('Bản phát hành thiếu nội dung Marketing đã duyệt.')
            widgets = marketing.get('widgets')
            if not isinstance(widgets, list):
                fail('Bản phát hành thiếu danh sách KPI.')
            view.metrics = []
            for widget in widgets:
                if not isinstance(widget, dict) or not text(widget.get('metric_id')):
                    fail('KPI phát hành không hợp lệ.')
                current = scalar(widget.get('value'))
                if current is not None and (widget.get('verified') is not True or widget.get('publishable') is not True):
                    fail('KPI chưa được xác minh.')
                previous = widget.get('comparison') or {}
                if not isinstance(previous, dict) or not isinstance(widget.get('freshness') or {}, dict):
                    fail('Kỳ so sánh hoặc độ mới KPI không hợp lệ.')
                view.metrics.append(MetricView(widget['metric_id'], text(widget.get('label')) or widget['metric_id'],
                    current, text(widget.get('unit')) or '', scalar(previous.get('previous_value')) if compare_ok else None,
                    scalar(previous.get('delta')) if compare_ok else None, text(widget.get('source')) or '',
                    text((widget.get('freshness') or {}).get('latest_available_date')), current is not None,
                    widget['metric_id'].split('.')[0]))
                if compare_ok and number(current) and number(previous.get('previous_value')):
                    view.charts.append(ChartView('So sánh · ' + (text(widget.get('label')) or widget['metric_id']),
                        'bar', ['Kỳ trước', 'Kỳ này'], [previous['previous_value'], current],
                        text(widget.get('source')) or '', text(widget.get('unit')) or ''))
            if not isinstance(data.get('executive_summary', {}), dict) or not isinstance(data.get('platforms', {}), dict):
                fail('Phạm vi kết luận hoặc danh mục nguồn không hợp lệ.')
            view.limitations = notes(data.get('executive_summary', {}).get('limitations'))
            view.approval = {key: data['release'].get(key) for key in ('version', 'reviewer_id', 'approved_at', 'approval_id')}
            view.platforms = [{'key': key, 'label': text(value.get('label')) or key, 'status': text(value.get('status')) or 'not_in_report',
                               'integration': text(value.get('integration')) or 'planned'}
                              for key, value in (data.get('platforms') or {}).items() if isinstance(value, dict)]
        view.state = 'available' if view.metrics or view.charts or view.tables or view.evidence or view.opportunities else 'empty'
        if view.valid is False or q.status == 'failed':
            view.state = 'partial' if view.state == 'available' else 'unavailable'
        return view

    def _source(self, view: SectionView, source_key: str, raw: dict, compare_ok: bool) -> None:
        table_start = len(view.tables)
        name = text(raw.get('label')) or SECTION_NAMES.get(source_key, source_key)
        latest = text(raw.get('latest_available_date'))
        source_notes = notes(raw.get('warnings'))
        view.sources.append(SourceView(name, text(raw.get('status')) or 'unknown', latest, text(raw.get('fetched_at')),
                                       safe_url(raw.get('url')), source_notes, text(raw.get('error')), 'demo' if demo(raw) else 'unverified'))
        view.quality.warnings.extend(f'{name}: {message}' for message in source_notes)
        if text(raw.get('error')):
            view.quality.warnings.append(f"{name}: {raw['error']}")
        totals = raw.get('totals', {})
        previous = raw.get('previous') if compare_ok and isinstance(raw.get('previous'), dict) else {}
        deltas = raw.get('deltas') if compare_ok and isinstance(raw.get('deltas'), dict) else {}
        if isinstance(totals, dict):
            for key, value in totals.items():
                if isinstance(value, dict) and not compare_ok:
                    value = {k: v for k, v in value.items() if k not in ('previous', 'delta')}
                view.metrics.append(self._metric(str(key), value, source_key, name, latest, previous.get(key), deltas.get(key)))
        else:
            view.quality.warnings.append(f'{name}: totals sai cấu trúc; không tạo KPI thay thế.')
        if isinstance(raw.get('kpis'), list):
            for entry in raw['kpis']:
                if isinstance(entry, dict) and text(entry.get('key')):
                    copy = {**entry}
                    if not compare_ok:
                        copy.pop('previous', None)
                        copy.pop('delta', None)
                    view.metrics.append(self._metric(entry['key'], copy, source_key, name, latest))
        for field, title in DETAIL_LISTS.items():
            if field not in raw:
                continue
            rows = raw[field]
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                view.quality.warnings.append(f'{name}: bảng {field} sai cấu trúc.')
                continue
            table = self._table(title, rows, source_key, name)
            view.tables.append(table)
            if field == 'daily' and rows:
                self._daily(view, rows, source_key, name, latest)
            if field == 'channels' and rows:
                labels = [text(r.get('sessionDefaultChannelGroup')) for r in rows]
                values = [r.get('sessions') if number(r.get('sessions')) else None for r in rows]
                if all(labels) and any(v is not None for v in values):
                    view.charts.append(ChartView('Phiên theo kênh', 'bar', labels, values, name, '', latest))
        self._explicit_charts(view, raw.get('charts'), name, latest)
        self._explicit_tables(view, raw.get('tables'), name)
        for table in view.tables[table_start:]:
            keys = {column['key'] for column in table.columns}
            if 'keyword' not in keys:
                continue
            # A saved per-row comparison has the same period requirements as a KPI.
            if not compare_ok:
                for row in table.rows:
                    for key in ('previous_position', 'change'):
                        if key in row:
                            row[key] = {'value': None, 'url': None}
            if source_key == 'keywords' and {'keyword', 'date', 'url'} <= keys:
                identities = [tuple(row[key]['value'] for key in ('keyword', 'date', 'url')) for row in table.rows]
                if len(identities) != len(set(identities)):
                    view.quality.warnings.append(
                        f'{name}: có bản ghi trùng từ khóa/ngày/URL. Giữ nguyên snapshot; '
                        'Top K đã chốt chưa chứng minh số từ khóa duy nhất. Cần Admin đối soát.')

    @staticmethod
    def _explicit_tables(view: SectionView, tables: object, source: str) -> None:
        """Optional presentation data; never require Admin to populate this shape."""
        if tables is None:
            return
        if not isinstance(tables, list):
            view.quality.warnings.append(f'{source}: tables chưa đúng cấu trúc renderer hỗ trợ.')
            return
        for entry in tables:
            if not isinstance(entry, dict):
                view.quality.warnings.append(f'{source}: bảng không hợp lệ.')
                continue
            columns, rows = entry.get('columns'), entry.get('rows')
            if (not isinstance(columns, list) or not columns or
                    not all(isinstance(c, dict) and text(c.get('key')) for c in columns) or
                    len({c['key'] for c in columns}) != len(columns) or
                    not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows)):
                view.quality.warnings.append(f'{source}: bảng thiếu cột/bản ghi hợp lệ.')
                continue
            cols = [dict(key=c['key'], label=text(c.get('label')) or c['key'], unit=text(c.get('unit')) or '') for c in columns]
            cells = [{c['key']: {'value': scalar(row.get(c['key'])), 'url': safe_url(row.get(c['key']))
                      if c['key'] in ('url', 'source_url', 'permalink_url') else None} for c in cols} for row in rows]
            view.tables.append(TableView(text(entry.get('title')) or 'Chi tiết', cols, cells, source, 'available' if cells else 'empty'))

    @staticmethod
    def _metric(key: str, value: object, source_key: str, source: str, latest: str | None, previous: object = None, delta: object = None) -> MetricView:
        entry = value if isinstance(value, dict) else {'value': value}
        current = scalar(entry.get('value'))
        return MetricView(key, text(entry.get('label')) or LABELS.get(key, key), current,
                          metric_unit(source_key, key, entry.get('unit')), scalar(entry.get('previous', previous)),
                          scalar(entry.get('delta', delta)), text(entry.get('source')) or source,
                          text(entry.get('data_date')) or latest, current is not None, source_key)

    @staticmethod
    def _table(title: str, rows: list[dict], source_key: str, source: str) -> TableView:
        keys = list(dict.fromkeys(key for row in rows for key, value in row.items() if value is None or type(value) in (str, int, float)))
        columns = [dict(key=key, label=LABELS.get(key, key), unit=metric_unit(source_key, key)) for key in keys]
        cells = []
        for row in rows:
            cells.append({key: {'value': scalar(row.get(key)), 'url': safe_url(row.get(key)) if key in ('url', 'source_url', 'permalink_url') else None} for key in keys})
        return TableView(title, columns, cells, source, 'available' if cells and columns else 'empty')

    @staticmethod
    def _daily(view: SectionView, rows: list[dict], source_key: str, name: str, latest: str | None) -> None:
        if any(not text(r.get('date')) for r in rows):
            view.quality.warnings.append(f'{name}: chuỗi theo ngày thiếu nhãn ngày; chỉ hiển thị bảng.')
            return
        try:
            dates = [date.fromisoformat(r['date']) for r in rows]
            if len(set(dates)) != len(dates) or any(d.isoformat() != r['date'] for d, r in zip(dates, rows)):
                raise ValueError()
            start, end = min(dates), max(dates)
            if (end - start).days > 3660:
                raise ValueError()
            by_date = {r['date']: r for r in rows}
            rows = [by_date.get((start + timedelta(days=i)).isoformat(), {'date': (start + timedelta(days=i)).isoformat()})
                    for i in range((end - start).days + 1)]
        except (ValueError, TypeError):
            view.quality.warnings.append(f'{name}: ngày bị trùng hoặc không hợp lệ; chỉ hiển thị bảng.')
            return
        keys = list(dict.fromkeys(key for row in rows for key, value in row.items() if key != 'date' and number(value)))
        for key in keys:
            view.charts.append(ChartView(LABELS.get(key, key) + ' theo ngày', 'line', [r['date'] for r in rows],
                                        [r[key] if number(r.get(key)) else None for r in rows], name, metric_unit(source_key, key), latest))

    @staticmethod
    def _explicit_charts(view: SectionView, charts: object, name: str, latest: str | None) -> None:
        if charts is None:
            return
        if not isinstance(charts, list):
            view.quality.warnings.append(f'{name}: charts chưa đúng cấu trúc renderer hỗ trợ.')
            return
        for raw in charts:
            if not isinstance(raw, dict):
                continue
            kind, labels, values = raw.get('type'), raw.get('labels'), raw.get('values')
            valid = kind in ('line', 'bar', 'donut') and isinstance(labels, list) and isinstance(values, list) and len(labels) == len(values) and all(isinstance(v, str) for v in labels) and all(v is None or number(v) for v in values)
            if not valid:
                view.quality.warnings.append(f'{name}: biểu đồ không hợp lệ hoặc chưa hỗ trợ.')
                continue
            if kind == 'line' and labels and all(len(label) == 10 and label[4:5] == '-' for label in labels):
                try:
                    dates = [date.fromisoformat(label) for label in labels]
                    if len(set(dates)) != len(dates) or (max(dates) - min(dates)).days > 3660:
                        raise ValueError()
                    points = dict(zip(labels, values))
                    labels = [(min(dates) + timedelta(days=i)).isoformat() for i in range((max(dates) - min(dates)).days + 1)]
                    values = [points.get(label) for label in labels]
                except ValueError:
                    view.quality.warnings.append(f'{name}: ngày biểu đồ bị trùng hoặc không hợp lệ.')
                    continue
            ready = bool(labels) and any(v is not None for v in values)
            if kind == 'donut' and (any(v is None or v < 0 for v in values) or not any(v and v > 0 for v in values)):
                ready = False
            view.charts.append(ChartView(text(raw.get('title')) or 'Biểu đồ nguồn', kind, labels, values, name,
                                        text(raw.get('unit')) or '', latest, 'available' if ready else 'unavailable'))

    @staticmethod
    def _evidence(entries: object, released: bool = False) -> list[EvidenceCard]:
        if not isinstance(entries, list):
            return []
        result = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get('review_status') != 'approved' or (released and entry.get('verification') != 'provider_origin_confirmed'):
                continue
            result.append(EvidenceCard(text(entry.get('claim')), text(entry.get('metric')), scalar(entry.get('before')),
                                       scalar(entry.get('after')), period(entry['period']) if isinstance(entry.get('period'), dict) else None,
                                       text(entry.get('source')), safe_url(entry.get('url')), text(entry.get('data_date')), quality(entry.get('quality')),
                                       'provider_origin_confirmed' if released else 'unverified', text(entry.get('asset_id')), text(entry.get('evidence_id'))))
        return result

    @staticmethod
    def _opportunities(entries: object, released: bool = False) -> list[OpportunityCard]:
        if not isinstance(entries, list):
            return []
        return [OpportunityCard(text(e.get('title')), text(e.get('reason')), notes(e.get('supporting_data')), text(e.get('priority')),
                                text(e.get('action')), notes(e.get('conditions'))) for e in entries
                if isinstance(e, dict) and released and e.get('review_status') == 'approved']
