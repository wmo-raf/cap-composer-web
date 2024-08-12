import logging
import json
import os
import time
import paho.mqtt.publish as publish
from base64 import b64encode, b64decode
from cryptography.fernet import Fernet

from cap.utils import serialize_and_sign_cap_alert

# Set log level
logging.basicConfig(level=logging.INFO)


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
        encrypted_password (str): The stored encrypted password

    Returns:
        str: The original password string entered by the user.
    """
    # Decrypt it using the Fernet key
    encrypted_password = b64decode(encrypted_password.encode())
    return cipher.decrypt(encrypted_password).decode()


def publish_cap_to_each_mqtt_broker(alert, alert_xml, broker):
    """Formats the message for MQTT publishing and publishes it
    to a given broker.

    Args:
        alert (CapAlertPage): The CAP alert instance to obtain metadata.
        alert_xml (bytes): The CAP alert XML bytes to be published.
        broker (CAPALertMQTTBroker): The broker configured by the user,
        containing details such as the host, port, and authentication.

    Raises:
        ex: An exception if the Paho MQTT publishing step fails
        after all retries.
    """

    from cap.models import CAPAlertMQTTBrokerEvent

    logging.info(
        f"""
        Publishing CAP Alert: {alert.title} ({alert.id}) to broker:
        {broker.name} - {broker.host}:{broker.port}
        """
    )

    event = CAPAlertMQTTBrokerEvent.objects.filter(
        broker=broker, alert=alert
    ).first()

    if not event:
        logging.info(
            f"No existing event found for broker: {broker.name}, creating new event"
        )
        event = CAPAlertMQTTBrokerEvent.objects.create(
            broker=broker,
            alert=alert,
            status="PENDING",
        )

    # Encode the CAP alert message in base64
    data = b64encode(alert_xml).decode()

    # Create the filename
    filename = f"{alert.status}-{alert.sent}-{alert.title}.xml"

    # Create the notification to be sent to the internal broker
    msg = {
        "centre_id": broker.centre_id,
        "is_recommended": broker.is_recommended,
        "data": data,
        "filename": filename,
        "_meta": {}
    }

    private_auth = {"username": broker.username,
                    "password": decrypt_password(broker.password)}

    # Publish notification on internal broker, using 5 retries
    # with an exponential backoff delay
    max_retries = 5
    initial_delay = 2
    for attempt in range(max_retries):
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
            logging.info(
                f"CAP Alert successfully published to MQTT broker: {broker.name}"
            )
            event.save()
            break
        except Exception as ex:
            logging.warning(
                f"CAP Alert MQTT Broker Event failed: {ex}",
                exc_info=True)
            event.status = "FAILURE"
            event.retries += 1
            event.error = str(ex)
            event.save()
            # Exponential backoff delays
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)
                logging.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise ex


def publish_cap_to_all_mqtt_brokers(cap_alert_id):
    """Automatically publishes the CAP alert to all MQTT brokers
    configured in the editor.

        cap_alert_id (int): The ID of the CAP alert, used to fetch
        the CAP alert instance from the database.
    """

    from cap.models import CapAlertPage, CAPAlertMQTTBroker

    logging.info(
        f"Starting publish_cap_mqtt_message for CAP Alert ID: {cap_alert_id}")

    # Get all active brokers
    brokers = CAPAlertMQTTBroker.objects.filter(active=True)
    logging.info(f"Found {len(brokers)} active brokers")

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

    for broker in brokers:
        publish_cap_to_each_mqtt_broker(cap_alert, alert_xml, broker)
