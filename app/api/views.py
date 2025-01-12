import asyncio
import json
import threading
from itertools import count
from time import sleep
from uuid import uuid4

from celery import shared_task
from django.db import connection
from django.db.models import Max
from django.http import HttpRequest, JsonResponse

from api.models import Log


# def retry_on_connection_error(func):
#     def inner(*args, **kwargs):
#         retries = 0
#         while retries < 3:
#             try:
#                 return func(*args, **kwargs)
#             except ConnectionError:
#                 print('--- CONNECTION ERROR ---')
#                 sleep(0.1)
#             except Exception as exc:
#                 raise exc
#             retries += 1
#     return inner


def flush_db(request: HttpRequest) -> JsonResponse:
    with connection.cursor() as cursor:
        cursor.execute('TRUNCATE TABLE api_log RESTART IDENTITY CASCADE;')
    assert Log.objects.count() == 0
    return JsonResponse({'message': 'OK'}, status=200)


def get_count(request: HttpRequest) -> JsonResponse:
    # Required to know the ID that we are starting at - otherwise, would need to flush DB every time
    count = Log.objects.aggregate(Max('id'))['id__max'] or 0
    return JsonResponse({'count': count}, status=200)


def get_logs(request: HttpRequest) -> JsonResponse:
    # want a way to pull out the log data for inspection later
    min_id = request.GET.get('min_id', 0)
    max_id = request.GET.get('max_id', 100_000_000)
    logs = Log.objects.filter(id__range=(min_id, max_id))
    return JsonResponse({'logs': [{
        'id': log.id,
        'i': log.data['i'],
        'uuid': log.uuid,
    } for log in logs]})


# NO-OP - just a latency measurer
def no_op(request: HttpRequest):
    return JsonResponse({'message': 'ok'}, status=201)

def low_op(request: HttpRequest):
    data = json.loads(request.body.decode('utf-8'))
    uuid = uuid4()
    return JsonResponse({'message': 'ok'}, status=201)


# SIMPLE METHOD
def create_log__simple(request: HttpRequest) -> JsonResponse:
    data = json.loads(request.body.decode('utf-8'))
    uuid = uuid4()
    log = Log.objects.create(data=data, uuid=uuid)
    return JsonResponse({'uuid': log.id}, status=201)


# DEFERRING TO CELERY
@shared_task
def create_log_task(log_params: dict):
    Log.objects.create(**log_params)

def create_log__deferred(request: HttpRequest) -> JsonResponse:
    data = json.loads(request.body.decode('utf-8'))

    uuid = uuid4()
    log_params = dict(data=data, uuid=uuid)
    create_log_task.delay(log_params)
    return JsonResponse({'uuid': uuid}, status=201)


# IN-MEMORY BATCHING
LOGS = []
BATCH_SIZE = 25

def create_log__batch(request: HttpRequest) -> JsonResponse:
    global LOGS
    data = json.loads(request.body.decode('utf-8'))

    uuid = uuid4()
    log = Log(data=data, uuid=uuid)
    LOGS.append(log)

    if len(LOGS) >= BATCH_SIZE:
        try:
            Log.objects.bulk_create(LOGS)
        except:
            for log in LOGS:
                log.save()
        LOGS = []

    return JsonResponse({'uuid': uuid}, status=201)
