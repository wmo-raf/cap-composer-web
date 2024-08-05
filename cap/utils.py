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
    """This function does the following:
    1. Takes an alert object and an optional request object and 
    serializes the alert using the AlertSerializer.
    2. Renders the serialized data into XML using the CapXMLRenderer.
    3. Includes a HTML stylesheet for styling the XML.

    Args:
        alert (object): The alert object to be serialized and signed.
        request (object, optional): The request object. Defaults to None.

    Returns:
        tuple: A tuple containing the serialized and signed XML as a
        bytes object and a boolean indicating whether the XML was signed
        or not.
    """
    from cap.serializers import AlertSerializer

    data = AlertSerializer(alert, context={
        "request": request,
    }).data

    xml = CapXMLRenderer().render(data)
    xml_bytes = bytes(xml, encoding='utf-8')

    # Try to sign the XML
    signed = False
    try:
        signed_xml = sign_xml(xml_bytes)
        if signed_xml:
            xml = signed_xml
            signed = True
    except Exception:
        pass

    if signed:
        root = etree.fromstring(xml)
    else:
        root = etree.fromstring(xml_bytes)

    style_url = get_full_url(request, reverse("cap_alert_stylesheet"))

    tree = etree.ElementTree(root)
    # Add stylesheet processing instruction
    pi = etree.ProcessingInstruction(
        'xml-stylesheet', f'type="text/xsl" href="{style_url}"')
    tree.getroot().addprevious(pi)
    xml = etree.tostring(tree, xml_declaration=True, encoding='utf-8')

    return xml, signed
