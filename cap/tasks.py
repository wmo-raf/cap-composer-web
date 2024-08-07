import logging
import json
import paho.mqtt.publish as publish
from base64 import b64encode


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
                        "password": broker.password}

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
