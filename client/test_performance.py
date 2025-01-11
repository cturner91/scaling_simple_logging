import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from datetime import datetime, timedelta
from functools import partial
from multiprocessing import cpu_count
from time import sleep
from typing import Any, Callable

import requests


N_REQUESTS = 100
N_SECONDS = 1
BASE_URL = "http://app:8456"
URLS = [
    f'{BASE_URL}/api/no-op/',
    f'{BASE_URL}/api/low-op/',
    f'{BASE_URL}/api/simple/',
    f'{BASE_URL}/api/deferred/',
    f'{BASE_URL}/api/in-memory-batch/',
]


def simple_parallel(
    tasks: dict[str, Callable],
    max_workers: int|None = None, 
    executor_class: type[ThreadPoolExecutor] | type[ProcessPoolExecutor] | None = None,
) -> dict[str, Any]:
    if executor_class is None:
        executor_class = ThreadPoolExecutor

    if max_workers is None:
        if executor_class is ProcessPoolExecutor:
            max_workers = min(cpu_count(), len(tasks) or 1)
        else:
            max_workers = len(tasks) or 1

    # validate tasks dict
    for name, task in tasks.items():
        if not callable(task):
            raise TypeError(f'Task spec for {name} incorrect - must be callable')
    
    results = {}
    with executor_class(max_workers=max_workers) as executor:

        # use the future itself as the key in this dict
        future_to_name = {executor.submit(task): name for name, task in tasks.items()}
        
        for future in as_completed(future_to_name):
            # this is a generator that returns results in whatever order they execute most quickly
            # no ordering is implied or expected
            name = future_to_name[future]
            try:
                results[name] = future.result()
            except Exception as exc:
                results[name] = exc
    
    return results


def submit(i: int, url: str) -> dict:
    data = {'i': i+1}  # This lets us compare insertion order in DB with request send order
    sleep(i / N_REQUESTS * N_SECONDS)

    retries = 0
    dt0 = datetime.now()
    while retries < 5:
        try:
            response = requests.post(url, json=data)
            if response.status_code == 201:
                break
        except:
            sleep(2**retries * 0.05)
            retries += 1
    dt1 = datetime.now()

    delta = (dt1 - dt0).total_seconds()
    result = {
        'time_taken': delta,
        'i': i,
        'retries': retries,
    }
    return result


def run_batch(url, flush: bool = True) -> dict:
    if flush:
        # wipe DB to make it a fair test
        flushed = False
        while not flushed:
            response = requests.get(f'{BASE_URL}/api/flush/')
            if response.status_code == 200:
                flushed = True

    # submit N_REQUESTS tasks over N_SECONDS seconds        
    tasks = {i: partial(submit, i=i, url=url) for i in range(N_REQUESTS)}
    results = simple_parallel(tasks)

    count_failed = 0
    total_time, total_retries = 0, 0
    for i, result in results.items():
        if isinstance(result, Exception):
            count_failed += 1
        else:
            total_time += result['time_taken']
            total_retries += result['retries']

    mean_time = total_time / (N_REQUESTS - count_failed)

    results = {
        'summary': {
            'count_failed': count_failed,
            'total_time': total_time,
            'total_retries': total_retries,
            'mean_time': mean_time,
        },
        'raw': results,
    }

    return results


if __name__ == '__main__':

    for url in URLS:
        results = run_batch(url, True)

        print(url)
        print('Count failed: ', results['summary']['count_failed'])
        print('Mean time: ', results['summary']['mean_time'])
        print('Total retries: ', results['summary']['total_retries'])
        print(' ')

        # print('\nData:')
        # for result in results.values():
        #     print(result)
