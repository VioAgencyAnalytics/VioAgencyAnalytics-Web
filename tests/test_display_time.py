from app.display_time import vietnam_time
from app.routes.pages import templates


def test_vietnam_timestamp_offsets_and_midnight():
    assert vietnam_time('2026-11-11T03:55:00Z') == '10:55 11/11/2026 GMT+7'
    assert vietnam_time('2026-11-11T20:30:00Z') == '03:30 12/11/2026 GMT+7'
    assert vietnam_time('2026-11-11T03:55:00') == vietnam_time('2026-11-11T10:55:00+07:00')
    assert vietnam_time(None) == 'Chưa ghi nhận'
    assert vietnam_time('invalid') == 'Chưa ghi nhận'


def test_template_macro_uses_same_timestamp_conversion():
    template = templates.env.from_string('{% macro stamp(v) %}{{ v | vietnam_time }}{% endmacro %}{{ stamp(value) }}')
    assert template.render(value='2026-11-11T20:30:00Z') == '03:30 12/11/2026 GMT+7'
