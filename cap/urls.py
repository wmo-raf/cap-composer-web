from django.urls import path

from .views import get_cap_xml, AlertListFeed, get_cap_feed_stylesheet, get_cap_alert_stylesheet

urlpatterns = [
    path("api/cap/rss.xml", AlertListFeed(), name="cap_alert_feed"),
    path("api/cap/<uuid:guid>.xml", get_cap_xml, name="cap_alert_xml"),
    path("cap-feed-style.xsl", get_cap_feed_stylesheet, name="cap_feed_stylesheet"),
    path("cap-style.xsl", get_cap_alert_stylesheet, name="cap_alert_stylesheet"),
]
