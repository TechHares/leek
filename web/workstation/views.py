import re
from datetime import datetime

import requests
from django.contrib import messages
from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin

from leek.common import locked, config


# Create your views here.
def dashboard(request):
    context = {
        'running_job': 2,
        'datasource_count': 4,
        'trader_count': 12,
        'strategy_count': 30
    }
    return render(request, 'workstation/dashboard.html', context)


class Filter(MiddlewareMixin):
    def __init__(self, get_response):
        self.check_flag = True
        super().__init__(get_response)

    def process_request(self, request):
        if request.path.startswith('/admin/workstation'):
            if self.check_flag and int(datetime.now().timestamp()) - request.session.get('lcvt', 0) > 3600 * 3:
                try:
                    self._check_version(request)
                except:
                    self.check_flag = False

    @locked()
    def _check_version(self, request):
        if datetime.now().timestamp() - request.session.get('lcvt', 0) < 3600 * 3:
            return
        request.session['lcvt'] = int(datetime.now().timestamp())
        res = requests.get('https://api.github.com/repos/li-shenglin/leek/releases/latest')
        js = res.json()
        arr = js["tag_name"][1:].split(".")
        if config.VERSION >= (int(arr[0]), int(arr[1]), int(arr[2])):
            return
        update_log = re.sub(r'<br/>(\s|<br/>)*', '<br/>', js["body"].replace("\n", "<br/>").replace("\t", "<br/>"))
        messages.warning(request, f"""
发现新版本: {js["tag_name"]}<br/><br/>
{update_log}<br/>

github: <a href="https://github.com/li-shenglin/leek" target="_blank" rel="noopener noreferrer">leek</>
""")