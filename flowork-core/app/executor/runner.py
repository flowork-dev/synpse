########################################################################
# WEBSITE https://flowork.cloud
# File NAME : C:\FLOWORK\flowork-core\app\executor\runner.py total lines 17 
########################################################################

from app.worker.pool import executor
from app.executor.watchdog import JobWatchdog
WATCHDOG_DEADLINE = int(os.getenv("CORE_JOB_DEADLINE_SECONDS", "120"))
wd = JobWatchdog(deadline_seconds=WATCHDOG_DEADLINE)
def submit_job(job_id:str, node_callable, *args, **kwargs):
    def _task():
        val, err = wd.run_with_deadline(job_id, node_callable, *args, **kwargs)
        if err:
            raise err
        return val
    executor.submit(_task)
