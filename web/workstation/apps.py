import json
import os
import sys
import time
from datetime import datetime
from decimal import Decimal
from multiprocessing import Process
from pathlib import Path
from threading import Thread

import psutil
from django.apps import AppConfig

sys.path.append(f'{Path(__file__).resolve().parent.parent.parent}')

from leek.common import logger, config


def is_worker_process():
    if os.name == 'nt' or os.name == 'posix':
        p = os.path.join(config.DATA_DIR, "work")
        if not os.path.exists(p):
            with open(p, "w") as f:
                f.write(str(os.getpid()))
                return True
        else:
            with open(p, "r") as f:
                first_line = f.readline().strip()
            try:
                process = psutil.Process(int(first_line))
                if "python" in process.name().lower():
                    return False
            except psutil.NoSuchProcess:
                pass
            os.remove(p)
            return is_worker_process()
    else:
        return os.getpgrp() == os.getpid() or os.getppid() == os.getpgrp()


class WorkstationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workstation'
    verbose_name = "策略工作台"
    verbose_name_plural = verbose_name

    def ready(self):
        if os.environ.get("DISABLE_WORKER") == "true":
            return
        logger.info("workstation ready")
        if is_worker_process():
            logger.info(f"启动任扫描线程")
            t = Thread(target=_scheduler, daemon=True)
            t.start()


def _scheduler():
    from .models import StrategyConfig
    from .worker import run_scheduler
    while True:
        time.sleep(20)
        queryset = StrategyConfig.objects.filter(status__in=(2, 3))
        logger.debug(f"扫描任务: %s", StrategyConfig.objects.filter(status__in=(2, 3)).count())
        children = psutil.Process().children(recursive=True)
        for x in children:
            if x.status() == psutil.STATUS_ZOMBIE:
                x.kill()
        ids = [x.pid for x in children if x.status() != psutil.STATUS_ZOMBIE and "python" in x.name().lower()]
        for strategy in queryset:
            if strategy.end_time is not None and datetime.timestamp(strategy.end_time) < datetime.now().timestamp():
                strategy.status = 1
                strategy.save()
            elif strategy.status == 2 or (strategy.process_id is None or strategy.process_id not in ids):
                data = json.loads(
                    json.dumps([strategy.data_source.to_dict(), strategy.to_dict(), strategy.trade.to_dict()],
                               default=default))
                p = Process(target=run_scheduler, args=data, daemon=True)
                p.start()
                ids.append(p.pid)
                logger.info(f"启动策进程，process_id={p.pid}")
                strategy.process_id = p.pid
                strategy.status = 3
                strategy.just_save()


def default(obj):
    if isinstance(obj, datetime):
        return datetime.timestamp(obj)
    if isinstance(obj, Decimal):
        return float(obj)
    return obj.__str__()
