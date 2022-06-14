import os
from celery import Celery
from celery.schedules import crontab
from pydantic import constr
from rpn import get_person, get_token, update_person
import asyncio

celery = Celery(__name__)
celery.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379")
celery.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379")
celery.conf.enable_utc = False


@celery.task(name="create_task", default_retry_delay=300, max_retries=5)
def create_task(iin: constr(min_length=12, max_length=12)):
    try:
        asyncio.run(get_person(iin))
        return True
    except:
        create_task_token()
        asyncio.run(update_person(iin))
        return True


@celery.task(name="update_data", default_retry_delay=300, max_retries=5)
def update_data(iin: constr(min_length=12, max_length=12)):
    try:
        asyncio.run(update_person(iin))
        return True
    except:
        if create_task_token() is True:
            asyncio.run(update_person(iin))
            return True
        return False


@celery.task(name="create_task_token")
def create_task_token():
    get_token()
    return True


celery.conf.beat_schedule = {
    'token_task': {
        'task': 'worker.create_task_token',
        'schedule': crontab(minute=0, hour='*/4')
    }
}
