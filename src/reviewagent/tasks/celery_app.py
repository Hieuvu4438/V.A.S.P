from celery import Celery

from reviewagent.config import get_settings

settings = get_settings()

app = Celery("reviewagent")
app.conf.update(
    broker_url=settings.celery.broker_url,
    result_backend=settings.celery.result_backend,
    task_default_queue=settings.celery.task_default_queue,
    timezone="UTC",
)
