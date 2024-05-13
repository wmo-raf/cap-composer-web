import logging

from django import template
from django.conf import settings

logger = logging.getLogger(__name__)
register = template.Library()


@register.filter
def django_settings(value):
    return getattr(settings, value, None)
