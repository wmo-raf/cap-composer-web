import logging
import json
import os
import paho.mqtt.publish as publish
from base64 import b64encode, b64decode
from cryptography.fernet import Fernet

from cap.utils import serialize_and_sign_cap_alert


def get_object_or_none(model_class, **kwargs):
    try:
        return model_class.objects.get(**kwargs)
    except model_class.DoesNotExist:
        return None


key = os.getenv('CAP_FERNET_KEY')
if key is None:
    raise ValueError("CAP_FERNET_KEY environment variable not set")
cipher = Fernet(key)


def decrypt_password(encrypted_password) -> str:
    """Decrypts the stored broker password
    and returns the original entered password.

    Args:
        encrypted_password (str): The stored encrypted password.

    Returns:
        str: The original password string entered by the user.
    """
    # Begin by removing the "ENCRYPTED:" prefix
    encrypted_password = encrypted_password.replace("ENCRYPTED:", "")
    # Now decrypt it using the Fernet key
    encrypted_password = b64decode(encrypted_password.encode())
    return cipher.decrypt(encrypted_password).decode()


def publish_cap_mqtt_message(cap_alert_id):
    from cap.models import (
        CapAlertPage, CAPAlertMQTTBroker, CAPAlertMQTTBrokerEvent
    )

    # Get all active brokers
    brokers = CAPAlertMQTTBroker.objects.filter(active=True)

    if not brokers:
        logging.warning("No MQTT brokers found")
        return

    # Get the cap alert data to be published
    cap_alert = get_object_or_none(CapAlertPage, id=cap_alert_id)

    if not cap_alert:
        logging.warning(f"CAP Alert: {cap_alert_id} not found")
        return

    if not cap_alert.live:
        logging.warning(f"CAP Alert: {cap_alert_id} is not published")
        return

    if cap_alert.status != "Actual":
        logging.warning(f"CAP Alert: {cap_alert_id} is not actionable")
        return

    # Get the processed CAP alert XML
    alert_xml, signed = serialize_and_sign_cap_alert(cap_alert)

    if not signed:
        logging.warning(f"CAP Alert: {cap_alert_id} not signed")
        # Continue to publish anyway, the acceptance/rejection of non-signed
        # alerts should be handled on the wis2box side

    # Publish the alert to all active brokers
    for broker in brokers:
        event = CAPAlertMQTTBrokerEvent.objects.filter(
            broker=broker, alert=cap_alert
        ).first()

        if not event:
            event = CAPAlertMQTTBrokerEvent.objects.create(
                broker=broker,
                alert=cap_alert,
                status="PENDING",
            )

        # Encode the CAP alert message in base64
        data = b64encode(alert_xml.encode()).decode()

        # Create the notification to be sent to the internal broker
        msg = {
            "centre_id": broker.centre,
            "is_recommended": broker.recommended,
            "data": data,
            "filename": cap_alert.identifier,
            "_meta": {},
        }

        private_auth = {"username": broker.username,
                        "password": decrypt_password(broker.password)}

        # Publish notification on internal broker
        try:
            publish.single(
                topic=broker.internal_topic,
                payload=json.dumps(msg),
                qos=1,
                retain=False,
                hostname=broker.host,
                port=int(broker.port),
                auth=private_auth,
            )
            event.status = "SUCCESS"
            event.save()
        except Exception as ex:
            logging.warning(f"CAP Alert MQTT Broker Event failed: {ex}")
            event.status = "FAILURE"
            event.retries += 1
            event.error = str(ex)
            event.save()
            raise ex
