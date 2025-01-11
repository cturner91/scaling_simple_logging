from django.db import models


class Log(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    uuid = models.UUIDField(db_index=True)
    data = models.JSONField()
