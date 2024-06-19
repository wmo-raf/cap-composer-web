from capeditor.models import CapAlertPageForm, AbstractCapAlertPage
from capeditor.pubsub.publish import publish_cap_mqtt_message
from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from wagtail import blocks
from wagtail.models import Page
from wagtail.signals import page_published

from cap.utils import get_cap_settings, format_date_to_oid


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
                    ref_alert_block = references_field.block.child_blocks[block_type].child_blocks[field_name]

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
                    self.add_error('info', _("Effective date cannot be earlier than the alert sent date."))

                if expires and sent and expires < sent:
                    self.add_error('info', _("Expires date cannot be earlier than the alert sent date."))

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

        except Exception as e:
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


def on_publish_cap_alert(sender, **kwargs):
    instance = kwargs['instance']

    # Catch and ignore any exceptions that may occur
    # We don't want to stop the alert publishing process if an exception occurs
    try:
        # publish to mqtt
        topic = "cap/alerts/all"
        publish_cap_mqtt_message(instance, topic)
    except Exception as e:
        pass


page_published.connect(on_publish_cap_alert, sender=CapAlertPage)


def get_all_published_alerts():
    return CapAlertPage.objects.all().live().filter(status="Actual", scope="Public").order_by('-sent')
