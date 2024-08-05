from django.conf import settings
from lxml import etree
from signxml import XMLSigner, SignatureMethod

cap_cert_path = getattr(settings, "CAP_CERT_PATH", "")
cap_private_key_path = getattr(settings, "CAP_PRIVATE_KEY_PATH", "")
cap_signature_method = getattr(
    settings, "CAP_SIGNATURE_METHOD", SignatureMethod.RSA_SHA256)


def sign_xml(xml_string):
    if not cap_cert_path or not cap_private_key_path:
        return None

    with open(cap_private_key_path, "rb") as key_file:
        key = key_file.read()

    with open(cap_cert_path, "rb") as cert_file:
        cert = cert_file.read()

    root = etree.fromstring(xml_string)
    signed_root = XMLSigner(signature_algorithm=cap_signature_method).sign(
        root, key=key, cert=cert
    )
    return etree.tostring(signed_root)
