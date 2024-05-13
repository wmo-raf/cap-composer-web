from django.db import models
from wagtail.contrib.settings.models import BaseSiteSetting
from wagtail.contrib.settings.registry import register_setting
from wagtail.images import get_image_model_string


@register_setting
class GlobalSettings(BaseSiteSetting):
    website_name = models.CharField(max_length=255, blank=True, null=True)
    logo = models.ForeignKey(
        get_image_model_string(),
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='+'
    )

    class Meta:
        verbose_name = "Global Settings"
