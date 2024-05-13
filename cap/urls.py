from django.urls import path

from .views import get_cap_xml, AlertListFeed, get_cap_stylesheet

urlpatterns = [
    path("api/cap/rss.xml", AlertListFeed(), name="cap_alert_feed"),
    path("api/cap/<uuid:identifier>.xml", get_cap_xml, name="cap_alert_xml"),
    path("cap-style.xsl", get_cap_stylesheet, name="cap_stylesheet"),
]
