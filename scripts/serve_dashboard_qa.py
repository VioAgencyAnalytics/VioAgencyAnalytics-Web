"""Isolated visual fixture server. No runtime DB, credentials or providers."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import uvicorn
import main
from app.config import Settings, get_settings
from app.routes import viewer
from tests.bundle_fixtures import published_bundle
from qa_dashboard_fixture import paired_fixture
from fastapi import Request
from app.routes.pages import templates
from app.repositories.viewer import ViewerError

bundle = published_bundle()
bundle['report']['id'] = 'rpt_' + 'a' * 32
originals, paired = paired_fixture()


@main.app.get('/__qa/original/{channel}')
def original_page(request: Request, channel: str):
    key = {'facebook_content':'fb_content', 'facebook_ads':'ads', 'tiktok':'video', 'youtube':'video'}.get(channel, channel)
    return templates.TemplateResponse(request=request, name='pages/'+channel+'/index.html',
        context={key:originals[channel], 'active_report':channel.replace('_','-'), 'title':channel})


class FixtureRepository:
    service_token = ''
    def get_bundle(self, report_id, revision=None):
        if report_id == bundle['report']['id']:
            return bundle
        if report_id == paired['report']['id']:
            return paired
        raise ViewerError(404, 'Không có fixture này.')


viewer.repository = lambda *args: FixtureRepository()
main.get_runtime_mode = lambda: Settings(_env_file=None, app_env='test', debug=False)
main.app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, app_env='test', debug=False)

if __name__ == '__main__':
    uvicorn.run(main.app, host='127.0.0.1', port=8083, access_log=False)
