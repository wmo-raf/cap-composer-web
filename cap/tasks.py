import logging
import json
import paho.mqtt.publish as publish
from base64 import b64encode

from background_task import background
from requests import Session
from requests.exceptions import RequestException
from wagtailcache.cache import clear_cache

from base.utils import get_object_or_none, get_first_page_of_pdf_as_image
from pages.cap.utils import (
    create_cap_area_map_image,
    create_cap_pdf_document, serialize_and_sign_cap_alert
)

from pages.cap.webhook_http import prepare_request


@background(schedule=5)
def create_cap_alert_multi_media(cap_alert_page_id, clear_cache_on_success=False):
    from .models import CapAlertPage

    try:
        cap_alert = get_object_or_none(CapAlertPage, id=cap_alert_page_id)

        if cap_alert:
            print("[CAP] Generating CAP Alert MultiMedia content for: ",
                  cap_alert.title)
            # create alert area map image
            cap_alert_area_map_image = create_cap_area_map_image(cap_alert)

            if cap_alert_area_map_image:
                print("[CAP] 1. CAP Alert Area Map Image created for: ",
                      cap_alert.title)
                cap_alert.alert_area_map_image = cap_alert_area_map_image
                cap_alert.save()

                # create_cap_pdf_document
                cap_preview_document = create_cap_pdf_document(
                    cap_alert, template_name="cap/alert_detail_pdf.html")
                cap_alert.alert_pdf_preview = cap_preview_document
                cap_alert.save()

                print("[CAP] 2. CAP Alert PDF Document created for: ",
                      cap_alert.title)

                file_id = cap_alert.last_published_at.strftime("%s")
                preview_image_filename = f"{cap_alert.identifier}_{file_id}_preview.jpg"

                sent = cap_alert.sent.strftime("%Y-%m-%d-%H-%M")
                preview_image_title = f"{sent} - Alert Preview"

                # get first page of pdf as image
                cap_preview_image = get_first_page_of_pdf_as_image(file_path=cap_preview_document.file.path,
                                                                   title=preview_image_title,
                                                                   file_name=preview_image_filename)

                print("[CAP] 3. CAP Alert Preview Image created for: ",
                      cap_alert.title)

                if cap_preview_image:
                    cap_alert.search_image = cap_preview_image
                    cap_alert.save()

                print("[CAP] CAP Alert MultiMedia content saved for: ",
                      cap_alert.title)

                if clear_cache_on_success:
                    clear_cache()
        else:
            print("[CAP] CAP Alert not found for ID: ", cap_alert_page_id)
    except Exception as e:
        print("[CAP] Error in create_cap_alert_multi_media: ", e)
        pass


@background(schedule=5)
def fire_alert_mqtt_brokers(cap_alert_id):
    from pages.cap.models import CapAlertPage, CAPAlertMQTTBroker, CAPAlertMQTTBrokerEvent

    brokers = CAPAlertMQTTBroker.objects.filter(active=True)

    if not brokers:
        logging.warning("No MQTT brokers found")
        return

    cap_alert = get_object_or_none(CapAlertPage, id=cap_alert_id)

    if not cap_alert:
        logging.warning(f"CAP Alert: {cap_alert_id} not found")
        return

    if not cap_alert.live:
        logging.warning(f"CAP Alert: {cap_alert_id} is not published")
        return

    if cap_alert.status != = "Actual" and cap_alert.scope != = "Public":
        logging.warning(f"CAP Alert: {cap_alert_id} is not Public")
        return

    alert_xml, signed = serialize_and_sign_cap_alert(cap_alert)

    for broker in brokers:
        req = prepare_request(broker, alert_xml)

        event = CAPAlertMQTTBrokerEvent.objects.filter(
            broker=broker, alert=cap_alert).first()

        if not event:
            event = CAPAlertMQTTBrokerEvent.objects.create(
                broker=broker,
                alert=cap_alert,
                status="PENDING",
            )

        # Encode the CAP alert message in base64
        data = b64encode(alert_xml.encode()).decode()

        # TODO: Check if broker.channel obtains the channel
        # from the webpage and what the precise difference is
        # between broker.channel and broker.topic
        msg = {
            'channel': broker.channel,
            'data': data,
            'filename': cap_alert.identifier,
            '_meta': {}
        }

        private_auth = {
            'username': broker.username,
            'password': broker.password
        }

        try:
            publish.single(topic=broker.topic,
                           payload=json.dumps(msg),
                           qos=1,
                           retain=False,
                           hostname=broker.host,
                           port=int(broker.port),
                           auth=private_auth)
            event.status = "SUCCESS"
            event.save()

        except Exception as ex:
            logging.warning(f"CAP Alert MQTT Broker Event failed: {ex}")
            event.status = "FAILURE"
            event.retries += 1
            event.error = str(ex)
            event.save()

            raise ex
