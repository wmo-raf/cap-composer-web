from capeditor.cap_settings import CapSetting
from capeditor.renderers import CapXMLRenderer
from django.urls import reverse
from lxml import etree
from wagtail.api.v2.utils import get_full_url
from wagtail.models import Site

from cap.sign import sign_xml


def get_cap_settings():
    site = Site.objects.get(is_default_site=True)
    cap_settings = CapSetting.for_site(site)
    return cap_settings


def format_date_to_oid(date):
    # Extract date components
    year = date.year
    month = date.month
    day = date.day
    hour = date.hour
    minute = date.minute
    second = date.second

    # Format components into OID
    oid_date = f"{year}.{month}.{day}.{hour}.{minute}.{second}"

    return oid_date


def serialize_and_sign_cap_alert(alert, request=None):
    from cap.serializers import AlertSerializer

    data = AlertSerializer(alert, context={
        "request": request,
    }).data

    xml = CapXMLRenderer().render(data)
    xml_bytes = bytes(xml, encoding='utf-8')
    signed = False

    try:
        signed_xml = sign_xml(xml_bytes)
        if signed_xml:
            xml = signed_xml
            signed = True
    except Exception as e:
        pass

    if signed:
        root = etree.fromstring(xml)
    else:
        root = etree.fromstring(xml_bytes)

    style_url = get_full_url(request, reverse("cap_alert_stylesheet"))

    tree = etree.ElementTree(root)
    pi = etree.ProcessingInstruction('xml-stylesheet', f'type="text/xsl" href="{style_url}"')
    tree.getroot().addprevious(pi)
    xml = etree.tostring(tree, xml_declaration=True, encoding='utf-8')

    return xml, signed
