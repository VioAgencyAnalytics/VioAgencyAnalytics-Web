"""How to read a KPI; provider values and customer targets are never changed."""

LOWER = {'cpc', 'cost_per_result', 'position'}
HIGHER = {'active_users', 'sessions', 'organic_sessions', 'page_views', 'engagement_rate', 'clicks', 'impressions',
          'ctr', 'leads', 'conversions', 'views', 'watch_minutes', 'average_view_seconds',
          'subscribers_gained', 'posts_published', 'post_views_lifetime', 'reactions_lifetime', 'comments_lifetime',
          'shares_lifetime', 'likes_lifetime', 'followers', 'website_clicks', 'call_clicks',
          'directions', 'search_mobile', 'maps_mobile'}


def trend(key):
    if key in LOWER:
        return {'direction': 'lower', 'guidance': 'Giá trị thấp hơn là chiều cải thiện của chỉ số.'}
    if key in HIGHER:
        return {'direction': 'higher', 'guidance': 'Giá trị cao hơn là chiều cải thiện của chỉ số; cần đọc cùng chất lượng kết quả.'}
    return {'direction': 'context', 'guidance': 'Đọc cùng kết quả và mục tiêu; tăng hoặc giảm chưa tự nói lên hiệu quả.'}


def effect(key, relation):
    direction = trend(key)['direction']
    if relation == 'equal':
        return {'effect': 'unchanged', 'effect_label': 'Không thay đổi'}
    if direction == 'context':
        return {'effect': 'context', 'effect_label': 'Đọc cùng kết quả'}
    better = relation == ('below' if direction == 'lower' else 'above')
    return {'effect': 'improved' if better else 'declined',
            'effect_label': 'Đúng chiều cải thiện' if better else 'Ngược chiều cải thiện'}


def goal_assessment(status, is_open=False):
    labels = {'not_set': 'Chưa đặt', 'no_data': 'Chưa có số liệu', 'currency_mismatch': 'Khác tiền tệ',
              'met': 'Đạt mục tiêu', 'below_target': 'Chưa đạt',
              'within_limit': 'Trong giới hạn', 'over_limit': 'Vượt giới hạn'}
    if is_open:
        labels.update(met='Đạt đến hiện tại', below_target='Đang thực hiện',
                      within_limit='Trong giới hạn hiện tại', over_limit='Đang vượt giới hạn')
    return {'label': labels.get(status, 'Chưa đủ dữ liệu'),
            'tone': 'in_progress' if is_open and status in ('below_target', 'within_limit') else status,
            'provisional': is_open}
