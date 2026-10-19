"""Production route isolation, with test-only Admin HTTP upstream on 8093."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import uvicorn
import main
from app.config import Settings, get_settings

settings = Settings(_env_file=None, debug=False, app_env='production', report_admin_base_url='http://127.0.0.1:8093',
    report_admin_public_url='http://localhost:8093', report_new_public_url='http://localhost:8084', report_service_token='isolated-service')
main.app.dependency_overrides[get_settings] = lambda: settings
main.get_runtime_mode = lambda: settings
if __name__ == '__main__':
    uvicorn.run(main.app, host='127.0.0.1', port=8084, access_log=False)
