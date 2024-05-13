from capeditor.cap_settings import CapSetting
from capeditor.renderers import CapXMLRenderer
from capeditor.serializers import AlertSerializer as BaseAlertSerializer
from django.contrib.syndication.views import Feed
from django.core.cache import cache
from django.core.validators import validate_email
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.feedgenerator import Rss201rev2Feed, rfc2822_date
from lxml import etree
from wagtail.api.v2.utils import get_full_url
from wagtail.models import Site

from .models import CapAlertPage
from .sign import sign_xml


class AlertSerializer(BaseAlertSerializer):
    class Meta(BaseAlertSerializer.Meta):
        model = CapAlertPage


def get_cap_xml(request, identifier):
    alert = get_object_or_404(CapAlertPage, identifier=identifier, status="Actual", live=True)
    xml_string = cache.get(f"cap_xml_{identifier}")

    if not xml_string:
        data = AlertSerializer(alert).data
        xml_string = CapXMLRenderer().render(data)
        xml_bytes = bytes(xml_string, encoding='utf-8')
        signed = False

        try:
            signed_xml = sign_xml(xml_bytes)
            if signed_xml:
                xml_string = signed_xml
                signed = True
        except Exception as e:
            pass

        if signed:
            root = etree.fromstring(xml_string)
        else:
            root = etree.fromstring(xml_bytes)

        tree = etree.ElementTree(root)
        style_url = get_full_url(request, reverse("cap_stylesheet"))
        pi = etree.ProcessingInstruction('xml-stylesheet', f'type="text/xsl" href="{style_url}"')
        tree.getroot().addprevious(pi)
        xml_string = etree.tostring(tree, encoding='utf-8')

        # cache for a day
        cache.set(f"cap_xml_{identifier}", xml_string, 60 * 60 * 24)

    return HttpResponse(xml_string, content_type="application/xml")


def get_cap_stylesheet(request):
    stylesheet = cache.get("cap_stylesheet")

    if not stylesheet:
        stylesheet = render_to_string("cap/cap_stylesheet.html").strip()
        # cache for 5 days
        cache.set("cap_stylesheet", stylesheet, 60 * 60 * 24 * 5)

    return HttpResponse(stylesheet, content_type="application/xml")


class CustomFeed(Rss201rev2Feed):
    content_type = 'application/xml'

    def add_root_elements(self, handler):
        super().add_root_elements(handler)
        pubDate = rfc2822_date(self.latest_post_date())
        handler.addQuickElement('pubDate', pubDate)


class AlertListFeed(Feed):
    feed_copyright = "public domain"
    language = "en"

    feed_type = CustomFeed

    @staticmethod
    def link():
        return reverse("cap_alert_feed")

    def title(self):
        try:
            site = Site.objects.get(is_default_site=True)
            if site:
                cap_setting = CapSetting.for_site(site)
                return f"Latest Official Public alerts from {cap_setting.sender_name}"

        except Exception:
            pass

        else:
            return "Latest Official Public alerts"

        return None

    def description(self):

        try:
            site = Site.objects.get(is_default_site=True)
            if site:
                cap_setting = CapSetting.for_site(site)
                return f"This feed lists the most recent Official Public alerts from {cap_setting.sender_name}"

        except Exception:
            pass

        else:
            return "This feed lists the most recent Official Public alerts"

        return None

    def items(self):
        alerts = CapAlertPage.objects.all().live().filter(status="Actual")
        return alerts

    def item_title(self, item):
        return item.title

    def item_link(self, item):
        return reverse("cap_alert_xml", args=[item.identifier])

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
        return [item.info[0].value.get('category')]
