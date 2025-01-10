from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'scaling.settings')

app = Celery('scaling')

# Use SQLite as both broker and result backend
app.conf.update(
    broker_url='sqla+sqlite:///celerydb.sqlite',  # SQLite database for message broker
    result_backend='db+sqlite:///celeryresults.sqlite',  # SQLite database for task results
)

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
