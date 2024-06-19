from capeditor.cap_settings import CapSetting
from django.contrib.syndication.views import Feed
from django.core.cache import cache
from django.core.validators import validate_email
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.feedgenerator import Rss201rev2Feed, rfc2822_date
from django.utils.translation import gettext as _
from django.utils.xmlutils import SimplerXMLGenerator
from wagtail.models import Site

from .models import CapAlertPage, get_all_published_alerts
from .utils import serialize_and_sign_cap_alert


def get_cap_xml(request, guid):
    alert = get_object_or_404(CapAlertPage, guid=guid)
    xml = cache.get(f"cap_alert_xml_{guid}")

    if not xml:
        xml, signed = serialize_and_sign_cap_alert(alert, request)

        if signed:
            # cache signed alerts for 5 days
            cache.set(f"cap_alert_xml_{guid}", xml, 60 * 60 * 24 * 5)

    return HttpResponse(xml, content_type="application/xml")


def get_cap_feed_stylesheet(request):
    stylesheet = cache.get("cap_feed_stylesheet")

    if not stylesheet:
        stylesheet = render_to_string("cap/cap_feed_stylesheet.html").strip()
        # cache for 5 days
        cache.set("cap_feed_stylesheet", stylesheet, 60 * 60 * 24 * 5)

    return HttpResponse(stylesheet, content_type="application/xml")


def get_cap_alert_stylesheet(request):
    stylesheet = cache.get("cap_stylesheet")

    if not stylesheet:
        stylesheet = render_to_string("cap/cap_alert_stylesheet.html").strip()
        # cache for 5 days
        cache.set("cap_stylesheet", stylesheet, 60 * 60 * 24 * 5)

    return HttpResponse(stylesheet, content_type="application/xml")


class CustomCAPFeed(Rss201rev2Feed):
    content_type = 'application/xml'

    def write(self, outfile, encoding):
        handler = SimplerXMLGenerator(outfile, encoding, short_empty_elements=True)
        handler.startDocument()

        # add stylesheet
        handler.processingInstruction('xml-stylesheet', f'type="text/xsl" href="{reverse("cap_feed_stylesheet")}"')

        handler.startElement("rss", self.rss_attributes())
        handler.startElement("channel", self.root_attributes())
        self.add_root_elements(handler)
        self.write_items(handler)
        self.endChannelElement(handler)
        handler.endElement("rss")

    def add_root_elements(self, handler):
        super().add_root_elements(handler)
        pubDate = rfc2822_date(self.latest_post_date())
        handler.addQuickElement('pubDate', pubDate)

        try:
            site = Site.objects.get(is_default_site=True)
            if site:
                cap_setting = CapSetting.for_site(site)
                logo = cap_setting.logo
                sender_name = cap_setting.sender_name

                if logo:
                    url = logo.get_rendition('original').url
                    url = site.root_url + url

                    if url:
                        # add logo image
                        handler.startElement('image', {})
                        handler.addQuickElement('url', url)

                        if sender_name:
                            handler.addQuickElement('title', sender_name)

                        if self.feed.get('link'):
                            handler.addQuickElement('link', site.root_url)

                        handler.endElement('image')

        except Exception as e:
            pass


class AlertListFeed(Feed):
    feed_copyright = "public domain"
    language = "en"

    feed_type = CustomCAPFeed

    @staticmethod
    def link():
        return reverse("cap_alert_feed")

    def title(self):
        title = _("Latest alerts")

        try:
            site = Site.objects.get(is_default_site=True)
            if site:
                cap_setting = CapSetting.for_site(site)
                if cap_setting.sender_name:
                    title = _("Latest alerts from %(sender_name)s") % {"sender_name": cap_setting.sender_name}
        except Exception:
            pass

        return title

    def description(self):
        description = _("Latest alerts")

        try:
            site = Site.objects.get(is_default_site=True)
            if site:
                cap_setting = CapSetting.for_site(site)
                if cap_setting.sender_name:
                    description = _("Latest alerts from %(sender_name)s") % {"sender_name": cap_setting.sender_name}
        except Exception:
            pass

        return description

    def items(self):
        alerts = get_all_published_alerts()
        return alerts

    def item_title(self, item):
        return item.title

    def item_link(self, item):
        return reverse("cap_alert_xml", args=[item.guid])

    def item_description(self, item):
        return item.info[0].value.get('description')

    def item_pubdate(self, item):
        return item.sent

    def item_enclosures(self, item):
        return super().item_enclosures(item)

    def item_guid(self, item):
        return item.identifier

    def item_author_name(self, item):
        try:
            site = Site.objects.get(is_default_site=True)
            if site:
                cap_setting = CapSetting.for_site(site)
                if cap_setting.sender_name:
                    return cap_setting.sender_name
        except Exception:
            pass

        return None

    def item_author_email(self, item):
        try:
            site = Site.objects.get(is_default_site=True)
            if site:
                cap_setting = CapSetting.for_site(site)
                if cap_setting.sender:
                    # validate if sender is email address
                    validate_email(cap_setting.sender)
                    return cap_setting.sender
        except Exception:
            pass

        return None

    def item_categories(self, item):
        categories = item.info[0].value.get('category')

        if isinstance(categories, str):
            categories = [categories]

        return categories
