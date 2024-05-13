from django.utils.functional import cached_property
from wagtail.models import Page

from cap.models import CapAlertPage


class HomePage(Page):
    subpage_types = [
        "cap.CapAlertPage"
    ]

    @cached_property
    def cap_alerts(self):
        alerts = CapAlertPage.objects.all().live().filter(status="Actual").order_by('-sent')
        alert_infos = []

        for alert in alerts:
            for alert_info in alert.infos:
                alert_infos.append(alert_info)

        alert_infos = sorted(alert_infos, key=lambda x: x.get("sent", {}), reverse=True)

        return alert_infos

    @cached_property
    def alerts_by_expiry(self):
        all_alerts = self.cap_alerts
        active_alerts = []
        past_alerts = []

        for alert in all_alerts:
            if alert.get("expired"):
                past_alerts.append(alert)
            else:
                active_alerts.append(alert)

        return {
            "active_alerts": active_alerts,
            "past_alerts": past_alerts
        }
