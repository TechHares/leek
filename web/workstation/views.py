import re
from datetime import datetime

from django.contrib import messages
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin

from leek.common import locked, config
from leek.common.utils import new_version


# Create your views here.
def dashboard(request):
    context = {
        'running_job': 2,
        'datasource_count': 4,
        'trader_count': 12,
        'strategy_count': 30
    }
    return render(request, 'workstation/dashboard.html', context)


SESSION_KEY = f"lcvt{config.VERSION[0]}{config.VERSION[1]}{config.VERSION[2]}"


class Filter(MiddlewareMixin):
    def __init__(self, get_response):
        self.check_flag = True
        super().__init__(get_response)

    def process_request(self, request):
        if request.path.startswith('/admin/workstation'):
            if self.check_flag and int(datetime.now().timestamp()) - request.session.get(SESSION_KEY, 0) > 3600 * 3:
                try:
                    self._check_version(request)
                except:
                    self.check_flag = False

    @locked()
    def _check_version(self, request):
        if datetime.now().timestamp() - request.session.get(SESSION_KEY, 0) < 3600 * 3:
            return
        request.session[SESSION_KEY] = int(datetime.now().timestamp())
        v, name, log = new_version()
        if config.VERSION >= v:
            return
        update_log = re.sub(r'<br/>(\s|<br/>)*', '<br/>', log.replace("\n", "<br/>").replace("\t", "<br/>"))
        messages.warning(request, f"""
发现新版本: {name}<br/><br/>
{update_log}<br/>

github: <a href="https://github.com/TechHares/leek" target="_blank" rel="noopener noreferrer">leek</>
""")
