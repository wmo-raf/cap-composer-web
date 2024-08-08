from capeditor.models import CapAlertPageForm, AbstractCapAlertPage
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from wagtail import blocks
from wagtail.models import Page
from wagtail.signals import page_published
from wagtail.admin.panels import FieldPanel, MultiFieldPanel

import os
from base64 import b64encode
from cryptography.fernet import Fernet

from cap.utils import get_cap_settings, format_date_to_oid
from cap.tasks import publish_cap_mqtt_message


class CapPageForm(CapAlertPageForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        references_field = self.fields.get("references")

        # here we update the alert reference field to use a PageChooserBlock limited to CAPAlertPage types.
        # we don't want to allow the user to select any other page type, only CAPAlertPage types.
        if references_field:
            for block_type, block in references_field.block.child_blocks.items():
                if block_type == "reference":
                    field_name = "ref_alert"
                    ref_alert_block = references_field.block.child_blocks[
                        block_type].child_blocks[field_name]

                    label = ref_alert_block.label or field_name
                    name = ref_alert_block.name
                    help_text = ref_alert_block._help_text

                    references_field.block.child_blocks[block_type].child_blocks[field_name] = blocks.PageChooserBlock(
                        page_type="cap.CapAlertPage",
                        help_text=help_text,
                    )
                    references_field.block.child_blocks[block_type].child_blocks[field_name].name = name
                    references_field.block.child_blocks[block_type].child_blocks[field_name].label = label

    def clean(self):
        cleaned_data = super().clean()

        # validate dates
        sent = cleaned_data.get("sent")
        alert_infos = cleaned_data.get("info")
        if alert_infos:
            for info in alert_infos:
                effective = info.value.get("effective")
                expires = info.value.get("expires")

                if effective and sent and effective < sent:
                    self.add_error(
                        'info', _("Effective date cannot be earlier than the alert sent date."))

                if expires and sent and expires < sent:
                    self.add_error(
                        'info', _("Expires date cannot be earlier than the alert sent date."))

        return cleaned_data

    def save(self, commit=True):
        if self.instance.info:
            # set the expires field to the value of the expires date in the info field
            info = self.instance.info[0]
            expires = info.value.get("expires")
            if expires:
                self.instance.expires = expires

        return super().save(commit=commit)


class CapAlertPage(AbstractCapAlertPage):
    base_form_class = CapPageForm

    template = "cap/cap_alert_detail.html"

    parent_page_types = ["home.HomePage"]
    subpage_types = []

    expires = models.DateTimeField(blank=True, null=True)

    content_panels = Page.content_panels + [
        *AbstractCapAlertPage.content_panels
    ]

    class Meta:
        ordering = ["-sent"]
        verbose_name = _("CAP Alert")

    @property
    def display_title(self):
        title = self.draft_title or self.title
        sent = self.sent.strftime("%Y-%m-%d %H:%M")
        return f"{self.status} - {sent} - {title}"

    def __str__(self):
        return self.display_title

    def get_admin_display_title(self):
        return self.display_title

    @property
    def identifier(self):
        identifier = self.guid
        try:
            cap_settings = get_cap_settings()
            wmo_oid = cap_settings.wmo_oid

            if wmo_oid:
                date_oid = format_date_to_oid(self.sent)
                identifier = f"urn:oid:{wmo_oid}.{date_oid}"

        except Exception:
            pass

        return identifier

    @cached_property
    def xml_link(self):
        return reverse("cap_alert_xml", args=(self.identifier,))

    @property
    def reference_alerts(self):
        if self.msgType == "Alert":
            return None

        alerts = []

        for ref in self.references:
            alert_page = ref.value.get("ref_alert")
            if alert_page:
                alerts.append(alert_page.specific)

        if alerts:
            # sort by date sent
            alerts = sorted(alerts, key=lambda x: x.sent)

        return alerts


# Generate a key for encrypting the MQTT broker password
# This should be done once and stored securely
key = os.getenv('CAP_FERNET_KEY')
if key is None:
    raise ValueError("CAP_FERNET_KEY environment variable not set")
cipher = Fernet(key)


class CAPAlertMQTTBroker(models.Model):
    name = models.CharField(max_length=255,
                            verbose_name=_("Name"),
                            help_text=_("Provide a name to identify the broker"))
    host = models.CharField(max_length=255,
                            verbose_name=_("Broker Host"),
                            help_text=_("Provide the broker host name or IP address"))
    port = models.CharField(max_length=255,
                            verbose_name=_("Broker Port"),
                            help_text=_("Provide the broker port number"))
    username = models.CharField(max_length=255,
                                verbose_name=_("Broker Username"))
    password = models.CharField(max_length=255,
                                          verbose_name=_("Broker Password"))
    centre_id = models.CharField(max_length=255,
                                 verbose_name=_("Centre ID"))
    is_recommended = models.BooleanField(
        default=False,
        verbose_name=_("WMO Recommended Data"),
        help_text=_("Check this box if the CAP alerts are not WMO core data."))
    internal_topic = models.CharField(
        max_length=255, default="wis2box/cap/publication",
        verbose_name=_("Internal Topic"),
        help_text=_("Provide the internal topic to publish the CAP alerts. If you are publishing to a WIS2 node, leave this unchanged."))
    active = models.BooleanField(default=True,
                                 verbose_name=_("Active"),
                                 help_text=_("Automatically publish CAP alerts to this broker"))
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    retry_on_failure = models.BooleanField(
        default=True, verbose_name=_("Retry on failure"))

    panels = [
        MultiFieldPanel([
            FieldPanel("name"),
            FieldPanel("host"),
            FieldPanel("port"),
        ], heading=_("Broker Information")),
        MultiFieldPanel([
            FieldPanel("username"),
            FieldPanel("password"),
        ], heading=_("Authentication")),
        MultiFieldPanel([
            FieldPanel("centre_id"),
            FieldPanel("is_recommended"),
            FieldPanel("internal_topic"),
        ], heading=_("Metadata")),
        FieldPanel("active"),
    ]

    def encrypt_password(self, raw_password):
        """Encrypts the entered password and stores it in the
        encrypted_password field, in this way the password stored
        in the database is not in plain text.

        Args:
            raw_password (str): The raw password string entered
            by the user.
        """
        # Encrypts to a byte string
        encrypted_password = cipher.encrypt(raw_password.encode())
        # Converts to a base64 string, with prefix "ENCRYPTED:"
        # to indicate that the password is encrypted
        self.password = "ENCRYPTED:" + \
            b64encode(encrypted_password).decode()

    def save(self, *args, **kwargs):
        """Overrides the save method to encrypt the password before
        saving to the database.
        """
        if not self.password.startswith("ENCRYPTED:"):
            self.encrypt_password(self.password)
        # If the password starts with "ENCRYPTED:", it means that
        # the password is already encrypted, so we can save it.
        super().save(*args, **kwargs)

    class Meta:
        ordering = ["-created"]
        verbose_name = _("MQTT Broker")
        verbose_name_plural = _("MQTT Brokers")

    def __str__(self):
        return f"{self.name} - {self.host}:{self.port}"


MQTT_STATES = [
    ("PENDING", _("Pending")),
    ("FAILURE", _("Failure")),
    ("SUCCESS", _("Success")),
]


class CAPAlertMQTTBrokerEvent(models.Model):
    broker = models.ForeignKey(
        CAPAlertMQTTBroker, on_delete=models.CASCADE, related_name="events")
    alert = models.ForeignKey(
        CapAlertPage, on_delete=models.CASCADE,
        related_name="mqtt_broker_events")
    status = models.CharField(max_length=40, choices=MQTT_STATES,
                              default="PENDING", verbose_name=_("Status"),
                              editable=False)
    retries = models.IntegerField(default=0, verbose_name=_("Retries"))
    error = models.TextField(blank=True, null=True,
                             verbose_name=_("Last Error Message"))
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("MQTT Broker Event")
        verbose_name_plural = _("MQTT Broker Events")

    def __str__(self):
        return f"{self.broker.name} - {self.alert.title}"


def on_publish_cap_alert(sender, **kwargs):
    instance = kwargs['instance']

    if instance.status == "Actual":
        try:
            publish_cap_mqtt_message(instance)
        except Exception:
            pass


def get_all_published_alerts():
    return CapAlertPage.objects.all().live().filter(
        status="Actual", scope="Public").order_by('-sent')


def get_currently_active_alerts():
    current_time = timezone.localtime()
    return get_all_published_alerts().filter(expires__gte=current_time)


page_published.connect(on_publish_cap_alert, sender=CapAlertPage)
