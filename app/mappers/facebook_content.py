"""Validate and copy the Admin-owned content contract; no metric calculation."""
from copy import deepcopy
from math import isfinite
from urllib.parse import urlsplit, parse_qs

from app.repositories.admin_bundle import AdminBundleContractError


def content_report(raw, source, period, released):
    if raw is None:
        return {}
    def require(condition):
        if not condition:
            raise AdminBundleContractError('Cấu trúc Facebook Content không khớp bản phát hành.')
    require(isinstance(raw, dict) and raw.get('schema_version') == 'facebook-content-report-v1')
    require(raw.get('source') == 'facebook_content' and raw.get('identity') == source.get('identity'))
    require(raw.get('period') == period and raw.get('timezone') == source.get('timezone'))
    require(raw.get('fetched_at') == source.get('fetched_at'))
    require(raw.get('review_status') == ('approved' if released else 'pending_review'))
    sections = raw.get('sections')
    require(isinstance(sections, dict) and set(sections) == {'overview', 'formats', 'topics', 'posts', 'engagement', 'reach', 'insights'})
    for key, item in sections.items():
        require(isinstance(item, dict) and item.get('key') == key and isinstance(item.get('rows'), list))
        require(item.get('status') in ('available', 'partial', 'unsupported', 'no_data', 'pending_review'))
        note = item.get('commentary')
        if note is not None:
            require(isinstance(note, dict) and note.get('origin') == 'editorial' and isinstance(note.get('text'), str))
            require(note.get('status') == ('approved' if released else 'pending_review'))
        if key in ('formats', 'topics'):
            for row in item['rows']:
                require(isinstance(row, dict) and isinstance(row.get('label'), str))
                require(type(row.get('count')) is int and row['count'] >= 0)
                require(type(row.get('percent')) in (int, float) and isfinite(row['percent']) and 0 <= row['percent'] <= 100)
    original = {row['post_id']: row for row in source.get('entries', [])}
    rows = sections['posts']['rows']
    require(all(isinstance(row, dict) and isinstance(row.get('post_id'), str) for row in rows))
    require(len(rows) == len(original) and {row['post_id'] for row in rows} == set(original))
    for row in rows:
        saved = original[row['post_id']]
        require(all(row.get(k) == saved.get(k) for k in ('date', 'title', 'message', 'format',
                    'reactions_lifetime', 'comments_lifetime', 'shares_lifetime')))
        require(all(row.get(k) is None for k in ('reach', 'engagements', 'engagement_rate', 'link_clicks')))
        url = row.get('permalink_url')
        if url is not None:
            require(isinstance(url, str))
            try:
                parsed = urlsplit(url)
                page, post = row['post_id'].split('_', 1)
                query = parse_qs(parsed.query)
                require(parsed.scheme == 'https' and parsed.hostname == 'www.facebook.com'
                        and not parsed.username and not parsed.password and parsed.port in (None, 443)
                        and page == source['identity']['external_id']
                        and (parsed.path == f'/{page}/posts/{post}' or
                             (parsed.path == '/permalink.php' and query == {'story_fbid': [post], 'id': [page]})))
            except ValueError:
                require(False)
    return deepcopy(raw)
