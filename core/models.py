from django.db import models


class Branch(models.Model):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Branches'

    def __str__(self):
        return self.name
