"""Presentation of saved Facebook observations; no transport or provider secrets."""
from collections import Counter
from datetime import date
import math
import re
from urllib.parse import urlencode


FORMATS = {'photo': ('Ảnh', 'image'), 'album': ('Album', 'photo_library'),
           'video': ('Video', 'play_circle'), 'link': ('Liên kết', 'link'),
           'unknown': ('Khác', 'article')}


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def amount(value):
    return f'{value:,.0f}'.replace(',', '.') if number(value) else 'Chưa có số liệu'


def day(value, short=False):
    try:
        parsed = date.fromisoformat(value[:10])
        return parsed.strftime('%d/%m' if short else '%d/%m/%Y')
    except (TypeError, ValueError):
        return 'Chưa có ngày'


def post_url(post, page_id):
    """Deep-link only this exact Page/Post pair; never guess a vanity/pfbid ID."""
    identity = post.get('post_id')
    if not isinstance(identity, str) or not re.fullmatch(r'[0-9]{1,40}_[0-9]{1,40}', identity):
        return None
    page, key = identity.split('_')
    if page != page_id:
        return None
    # Numeric Page/Post IDs from the attested snapshot identify the exact story,
    # even when an older normalizer discarded Meta's vanity/pfbid permalink.
    return 'https://www.facebook.com/permalink.php?' + urlencode({'story_fbid': key, 'id': page})


def chart(key, title, rows, note, *, meta=False):
    values = [row['value'] for row in rows if number(row.get('value'))]
    maximum = max(values, default=0)
    raw_step = max(1, maximum / 3)
    magnitude = 10 ** math.floor(math.log10(raw_step))
    tick_step = math.ceil(raw_step / magnitude) * magnitude
    scale = tick_step * 3
    # Stable SVG coordinates avoid CSS percentage-height ambiguity and print well.
    left, width, top, height = 56, 792, 22, 186
    step = width / max(1, len(rows))
    points = []
    label_step = max(1, math.ceil(len(rows) / 8))
    for index, row in enumerate(rows):
        value = row.get('value')
        bar_height = height * value / scale if number(value) else 0
        stamp = row.get('date') or ''
        points.append({'x': round(left + index * step + step * .19, 2),
                       'y': round(top + height - bar_height, 2), 'height': round(bar_height, 2),
                       'width': round(step * .62, 2), 'center': round(left + (index + .5) * step, 2),
                       'value': value, 'display': amount(value), 'date': stamp,
                       'label': day(stamp, True), 'full_date': day(stamp),
                       'show_label': index in (0, len(rows) - 1) or (index % label_step == 0
                           and len(rows) - 1 - index >= max(2, label_step // 2))})
    ticks = [{'y': top + height - height * i / 3, 'label': amount(round(scale * i / 3))} for i in range(4)]
    return {'key': key, 'title': title, 'points': points, 'ticks': ticks, 'note': note,
            'meta': meta, 'has_data': bool(values), 'coverage': len(values), 'expected': len(rows)}


def build_view(content, details):
    metrics = {row['key']: row for row in content.get('metrics', [])}
    posts = content.get('posts', [])
    page_id = (content.get('asset') or {}).get('external_id')
    enriched = []
    for row in posts:
        message = row.get('message') or row.get('title') or 'Bài đăng không có nội dung chữ'
        first = next((line.strip() for line in message.splitlines() if line.strip()), message)
        kind = row.get('format') if row.get('format') in FORMATS else 'unknown'
        enriched.append({**row, 'heading': first[:160], 'url': post_url(row, page_id),
                         'date_label': day(row.get('date')), 'kind': kind,
                         'format_label': FORMATS[kind][0], 'format_icon': FORMATS[kind][1]})
    total_views = sum(p['post_media_view_lifetime'] for p in posts) if posts and all(number(p.get('post_media_view_lifetime')) for p in posts) else None
    cards = [
        {'key': 'posts_published', 'label': 'Bài đăng', 'value': metrics.get('posts_published', {}).get('value'), 'icon': 'article', 'tone': 'blue', 'note': 'Xuất bản trong kỳ · UTC'},
        {'key': 'post_views_lifetime', 'label': 'Lượt xem các bài', 'value': total_views, 'icon': 'visibility', 'tone': 'violet', 'note': 'Tích lũy của các bài trong kỳ',
         'help': 'Cộng lượt xem tích lũy của từng bài khi đủ số liệu. Không phải lượt xem phát sinh trong kỳ, không phải người xem duy nhất hay lượt xem toàn Fanpage.'},
        {'key': 'reactions_lifetime', 'label': 'Cảm xúc', 'value': metrics.get('reactions_lifetime', {}).get('value'), 'icon': 'favorite', 'tone': 'rose', 'note': 'Tích lũy của các bài trong kỳ'},
        {'key': 'comments_lifetime', 'label': 'Bình luận', 'value': metrics.get('comments_lifetime', {}).get('value'), 'icon': 'chat_bubble', 'tone': 'amber', 'note': 'Tích lũy của các bài trong kỳ'},
    ]
    insights = {row['metric']: row for row in content.get('insights', [])}
    charts = [chart('publishing', 'Nhịp đăng bài', [{'date': r['date'], 'value': r['posts_published']} for r in content.get('daily_posts', [])], 'Số bài xuất bản mỗi ngày UTC trong kỳ đã chọn.')]
    for key, label in [('page_media_view', 'Lượt xem toàn Fanpage'), ('page_post_engagements', 'Tương tác toàn Fanpage')]:
        item = insights.get(key)
        if item and item.get('values'):
            charts.append(chart(key, label, [{'date': p.get('end_time'), 'value': p.get('value')} for p in item['values']],
                'Toàn Fanpage · hiển thị từng mốc kết thúc ngày Meta. Không gán vào ngày đăng bài hoặc cộng thành tổng kỳ UTC.', meta=True))
    observations = []
    for key, label, note in [('page_follows', 'Người theo dõi', 'Tổng tại mốc Meta gần nhất có số liệu'),
                             ('page_total_media_view_unique', 'Người xem duy nhất', 'Trong một ngày Meta, không phải toàn kỳ')]:
        item = insights.get(key, {})
        valid = [p for p in item.get('values', []) if number(p.get('value'))]
        last = max(valid, key=lambda p: p.get('end_time') or '') if valid else None
        observations.append({'key': key, 'label': label, 'value': last['value'] if last else None,
                             'date': last.get('end_time') if last else None, 'note': note})
    distribution = Counter(p['kind'] for p in enriched)
    formats = [{'key': key, 'label': FORMATS[key][0], 'icon': FORMATS[key][1], 'count': count,
                'percent': round(100 * count / len(posts), 1)} for key, count in distribution.most_common()]
    issues = []
    shares = metrics.get('shares_lifetime', {})
    if shares.get('value') is None:
        coverage = shares.get('coverage') or {}
        issues.append({'title': 'Tổng chia sẻ chưa đầy đủ', 'note': f"Có số đếm ở {coverage.get('available', 0)}/{coverage.get('expected', len(posts))} bài. Bài chưa có số đếm được giữ là thiếu dữ liệu, không đổi thành 0."})
    if any(m.get('report_status') == 'period_boundary_mismatch' for m in insights.values()):
        issues.append({'title': 'Mốc ngày Meta khác ngày UTC', 'note': 'Chuỗi Insights vẫn có số liệu và được hiển thị trên biểu đồ. Chưa cộng thành tổng kỳ UTC vì ranh giới ngày không trùng khớp.'})
    unsupported = [m['label'] for m in content.get('metrics', []) if m.get('value') is None and m.get('status') == 'unsupported']
    if unsupported:
        issues.append({'title': 'Một số chỉ số chưa được cung cấp', 'note': ', '.join(unsupported) + '. Không suy ra từ lượt xem, số người theo dõi hoặc chỉ số quảng cáo.'})
    ranking = 'post_media_view_lifetime' if any(number(p.get('post_media_view_lifetime')) for p in enriched) else 'reactions_lifetime'
    top = sorted((p for p in enriched if number(p.get(ranking))), key=lambda p: (p[ranking], p.get('date') or ''), reverse=True)[:3]
    period = content.get('snapshot') or {}
    active_days = sum(p['posts_published'] > 0 for p in content.get('daily_posts', []))
    return {'cards': cards, 'posts': enriched, 'top': top, 'ranking': ranking,
            'ranking_label': 'lượt xem' if ranking == 'post_media_view_lifetime' else 'cảm xúc',
            'charts': charts, 'observations': observations, 'formats': formats, 'issues': issues,
            'shares': shares, 'active_days': active_days, 'days': len(content.get('daily_posts', [])),
            'period': day(period.get('start_date')) + ' – ' + day(period.get('end_date')),
            'single_brand': details.get('workspace', {}).get('kind') == 'business' and len(details.get('clients', [])) == 1}
