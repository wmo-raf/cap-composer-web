import json
from datetime import datetime

import pytz
from capeditor.cap_settings import get_cap_contact_list, get_cap_audience_list
from capeditor.models import CapSetting
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _, gettext
from wagtail import hooks
from wagtail.actions.copy_page import CopyPageAction
from wagtail.admin import messages
from wagtail.admin.forms.pages import CopyForm
from wagtail.admin.menu import MenuItem, Menu
from wagtail.blocks import StreamValue
from wagtail.models import Page
from wagtail_modeladmin.helpers import (
    AdminURLHelper,
    PagePermissionHelper,
    PermissionHelper,
    PageButtonHelper
)
from wagtail_modeladmin.options import (
    ModelAdmin,
    ModelAdminGroup,
    modeladmin_register
)
from wagtail_modeladmin.menus import GroupMenuItem

from home.models import HomePage
from cap.models import (
    CapAlertPage,
    CAPAlertMQTTBroker,
    CAPAlertMQTTBrokerEvent
)


class CAPPagePermissionHelper(PagePermissionHelper):
    def user_can_edit_obj(self, user, obj):
        can_edit = super().user_can_edit_obj(user, obj)

        if obj.live and obj.status == "Actual":
            return False

        return can_edit

    def user_can_delete_obj(self, user, obj):
        can_delete = super().user_can_delete_obj(user, obj)

        if obj.live and obj.status == "Actual":
            return False

        return can_delete

    def user_can_unpublish_obj(self, user, obj):
        can_unpublish = super().user_can_unpublish_obj(user, obj)

        if obj.live and obj.status == "Actual":
            return False

        return can_unpublish


class CAPAlertPageButtonHelper(PageButtonHelper):
    def get_buttons_for_obj(self, obj, exclude=None, classnames_add=None, classnames_exclude=None):
        buttons = super().get_buttons_for_obj(
            obj, exclude, classnames_add, classnames_exclude)

        classnames = self.edit_button_classnames + classnames_add
        cn = self.finalise_classname(classnames, classnames_exclude)

        if obj.live:
            live_button = {
                "url": obj.get_full_url(),
                "label": _("LIVE"),
                "classname": cn,
                "title": _("Visit the live page")
            }

            buttons = [live_button] + buttons

        return buttons


class CAPAdmin(ModelAdmin):
    model = CapAlertPage
    menu_label = _('Alerts')
    menu_icon = 'list-ul'
    menu_order = 200
    add_to_settings_menu = False
    exclude_from_explorer = False
    permission_helper_class = CAPPagePermissionHelper
    button_helper_class = CAPAlertPageButtonHelper


class CAPAlertMQTTAdmin(ModelAdmin):
    model = CAPAlertMQTTBroker
    menu_label = CAPAlertMQTTBroker._meta.verbose_name_plural
    menu_icon = 'globe'
    list_display = ('name', 'host', 'port', 'centre_id', 'created', 'modified')
    list_filter = ('centre_id', 'is_recommended', 'active')
    search_fields = ('name', 'centre_id')


class CAPAlertMQTTEventPermissionHelper(PermissionHelper):
    def user_can_create(self, user):
        return False

    def user_can_edit_obj(self, user, obj):
        return False

    def user_can_delete_obj(self, user, obj):
        return False

    def user_can_copy_obj(self, user, obj):
        return False


class CAPAlertMQTTEventAdmin(ModelAdmin):
    model = CAPAlertMQTTBrokerEvent
    menu_label = CAPAlertMQTTBrokerEvent._meta.verbose_name_plural
    menu_icon = 'notification'
    list_display = ('broker', 'alert', 'created', 'status')
    list_filter = ('broker', 'status')
    inspect_view_enabled = True

    permission_helper_class = CAPAlertMQTTEventPermissionHelper


class CAPMenuGroupAdminMenuItem(GroupMenuItem):
    def is_shown(self, request):
        return request.user.has_perm("base.can_view_alerts_menu")


class CAPMenuGroup(ModelAdminGroup):
    menu_label = _('CAP Alerts')
    menu_icon = 'warning'  # change as required
    menu_order = 200  # will put in 3rd place (000 being 1st, 100 2nd)
    items = (CAPAdmin, CAPAlertMQTTAdmin, CAPAlertMQTTEventAdmin)

    def get_menu_item(self, order=None):
        if self.modeladmin_instances:
            submenu = Menu(items=self.get_submenu_items())
            return CAPMenuGroupAdminMenuItem(
                self, self.get_menu_order(), submenu
            )

    def get_submenu_items(self):
        menu_items = []
        item_order = 1

        for modeladmin in self.modeladmin_instances:
            menu_items.append(modeladmin.get_menu_item(order=item_order))
            item_order += 1

        try:
            # Add CAP import menu
            settings_url = reverse("load_cap_alert")
            import_cap_menu = MenuItem(
                label=_("Import CAP Alert"), url=settings_url, icon_name="upload")
            menu_items.append(import_cap_menu)

            # Add base settings menu
            settings_url = reverse(
                "wagtailsettings:edit",
                args=[CapSetting._meta.app_label,
                      CapSetting._meta.model_name, ],
            )
            gm_settings_menu = MenuItem(
                label=_("CAP Base Settings"), url=settings_url, icon_name="cog")
            menu_items.append(gm_settings_menu)
        except Exception:
            pass

        return menu_items


modeladmin_register(CAPMenuGroup)


@hooks.register('construct_settings_menu')
def hide_settings_menu_item(request, menu_items):
    hidden_settings = ["cap-settings"]
    menu_items[:] = [
        item for item in menu_items if item.name not in hidden_settings]


@hooks.register("before_copy_page")
def copy_cap_alert_page(request, page):
    if page.specific.__class__.__name__ == "CapAlertPage":
        # Parent page defaults to parent of source page
        parent_page = page.get_parent()

        # Check if the user has permission to publish subpages on the parent
        can_publish = parent_page.permissions_for_user(
            request.user).can_publish_subpage()

        # Create the form
        form = CopyForm(
            request.POST or None, user=request.user, page=page, can_publish=can_publish
        )

        # Remove the publish_copies and alias fields from the form
        if form.fields.get("publish_copies"):
            form.fields.pop("publish_copies")

        if form.fields.get("alias"):
            form.fields.pop("alias")

        # Check if user is submitting
        if request.method == "POST":
            # Prefill parent_page in case the form is invalid (as prepopulated value for the form field,
            # because ModelChoiceField seems to not fall back to the user given value)
            parent_page = Page.objects.get(id=request.POST["new_parent_page"])

            if form.is_valid():
                # Receive the parent page (this should never be empty)
                if form.cleaned_data["new_parent_page"]:
                    parent_page = form.cleaned_data["new_parent_page"]

                action = CopyPageAction(
                    page=page,
                    recursive=form.cleaned_data.get("copy_subpages"),
                    to=parent_page,
                    update_attrs={
                        "title": form.cleaned_data["new_title"],
                        "slug": form.cleaned_data["new_slug"],
                        "sent": timezone.localtime(),
                    },
                    keep_live=False,
                    copy_revisions=False,
                    user=request.user,
                )
                new_page = action.execute()

                messages.success(
                    request,
                    _("Alert '%(page_title)s' copied. You can edit the new alert below.")
                    % {"page_title": page.specific_deferred.get_admin_display_title()},
                )

                for fn in hooks.get_hooks("after_copy_page"):
                    result = fn(request, page, new_page)
                    if hasattr(result, "status_code"):
                        return result

                # redirect to the edit copied page
                return redirect(reverse("wagtailadmin_pages:edit", args=(new_page.id,)))

        return TemplateResponse(
            request,
            "wagtailadmin/pages/copy.html",
            {
                "page": page,
                "form": form,
            },
        )

    return


@hooks.register("before_edit_page")
def before_edit_cap_alert_page(request, page):
    page = page.specific
    if page.__class__.__name__ == "CapAlertPage":
        if page.live and page.status == "Actual":
            url = AdminURLHelper(page).get_action_url("index")
            messages.warning(request, gettext(
                "Actual Alerts cannot be edited after they have been published. To publish an update to this alert, "
                "create a new alert of Message Type 'Update' and reference this alert"))
            return redirect(url)


@hooks.register("before_unpublish_page")
def before_unpublish_cap_alert_page(request, page):
    page = page.specific
    if page.__class__.__name__ == "CapAlertPage":
        if page.live and page.status == "Actual":
            url = AdminURLHelper(page).get_action_url("index")
            messages.warning(request, gettext(
                "Actual Alerts cannot be Unpublished after they have been published"))
            return redirect(url)


@hooks.register("before_delete_page")
def before_delete_cap_alert_page(request, page):
    page = page.specific
    if page.__class__.__name__ == "CapAlertPage":
        if page.live and page.status == "Actual":
            url = AdminURLHelper(page).get_action_url("index")
            messages.warning(request, gettext(
                "Actual Alerts cannot be deleted after they have been published. To cancel or publish an update "
                "to this alert, create a new alert of Message Type 'Cancel' or 'Update' and reference this alert"))
            return redirect(url)


@hooks.register("before_import_cap_alert")
def import_cap_alert(request, alert_data):
    cap_settings = CapSetting.for_request(request)
    hazard_event_types = cap_settings.hazard_event_types.all()

    base_data = {}

    # an alert page requires a title
    # here we use the headline of the first info block
    title = None

    if "sender" in alert_data:
        base_data["sender"] = alert_data["sender"]
    if "sent" in alert_data:
        sent = alert_data["sent"]
        # convert dates to local timezone
        sent = datetime.fromisoformat(sent).astimezone(pytz.utc)
        sent_local = sent.astimezone(timezone.get_current_timezone())
        base_data["sent"] = sent_local
    if "status" in alert_data:
        base_data["status"] = alert_data["status"]
    if "msgType" in alert_data:
        base_data["msgType"] = alert_data["msgType"]
    if "scope" in alert_data:
        base_data["scope"] = alert_data["scope"]
    if "restriction" in alert_data:
        base_data["restriction"] = alert_data["restriction"]
    if "note" in alert_data:
        base_data["note"] = alert_data["note"]

    info_blocks = []

    if "info" in alert_data:
        for info in alert_data.get("info"):
            info_base_data = {}

            if "language" in info:
                info_base_data["language"] = info["language"]
            if "category" in info:
                info_base_data["category"] = info["category"]
            if "event" in info:
                event = info["event"]

                existing_hazard_event_type = hazard_event_types.filter(
                    event__iexact=event).first()
                if existing_hazard_event_type:
                    info_base_data["event"] = existing_hazard_event_type.event
                else:
                    hazard_event_types.create(setting=cap_settings, is_in_wmo_event_types_list=False, event=event,
                                              icon="warning")
                    info_base_data["event"] = event

            if "responseType" in info:
                response_types = info["responseType"]
                response_type_data = []
                for response_type in response_types:
                    response_type_data.append({"response_type": response_type})
                info_base_data["responseType"] = response_type_data

            if "urgency" in info:
                info_base_data["urgency"] = info["urgency"]
            if "severity" in info:
                info_base_data["severity"] = info["severity"]
            if "certainty" in info:
                info_base_data["certainty"] = info["certainty"]
            if "eventCode" in info:
                event_codes = info["eventCode"]
                event_code_data = []
                for event_code in event_codes:
                    event_code_data.append(
                        {"valueName": event_code["valueName"], "value": event_code["value"]})
                info_base_data["eventCode"] = event_code_data
            if "effective" in info:
                effective = info["effective"]
                effective = datetime.fromisoformat(
                    effective).astimezone(pytz.utc)
                effective_local = effective.astimezone(
                    timezone.get_current_timezone())
                info_base_data["effective"] = effective_local
            if "onset" in info:
                onset = info["onset"]
                onset = datetime.fromisoformat(onset).astimezone(pytz.utc)
                onset_local = onset.astimezone(timezone.get_current_timezone())
                info_base_data["onset"] = onset_local
            if "expires" in info:
                expires = info["expires"]
                expires = datetime.fromisoformat(expires).astimezone(pytz.utc)
                expires_local = expires.astimezone(
                    timezone.get_current_timezone())
                info_base_data["expires"] = expires_local
            if "senderName" in info:
                info_base_data["senderName"] = info["senderName"]
            if "headline" in info:
                info_base_data["headline"] = info["headline"]
                if not title:
                    title = info["headline"]

            if "description" in info:
                info_base_data["description"] = info["description"]
            if "instruction" in info:
                info_base_data["instruction"] = info["instruction"]
            if "contact" in info:
                contact = info["contact"]
                contact_list = get_cap_contact_list(request)
                if contact not in contact_list:
                    cap_settings.contacts.append(
                        ("contact", {"contact": contact}))
                    cap_settings.save()
                info_base_data["contact"] = contact
            if "audience" in info:
                audience = info["audience"]
                audience_list = get_cap_audience_list(request)
                if audience not in audience_list:
                    cap_settings.audience_types.append(
                        ("audience_type", {"audience": audience}))
                    cap_settings.save()
                info_base_data["audience"] = audience

            if "parameter" in info:
                parameters = info["parameter"]
                parameter_data = []
                for parameter in parameters:
                    parameter_data.append(
                        {"valueName": parameter["valueName"], "value": parameter["value"]})
                info_base_data["parameter"] = parameter_data
            if "resource" in info:
                resources = info["resource"]
                resource_data = []
                for resource in resources:
                    if resource.get("uri") and resource.get("resourceDesc"):
                        resource_data.append({
                            "type": "external_resource",
                            "value": {
                                "external_url": resource["uri"],
                                "resourceDesc": resource["resourceDesc"]
                            }
                        })
                info_base_data["resource"] = resource_data

            areas_data = []
            if "area" in info:
                for area in info.get("area"):
                    area_data = {}
                    areaDesc = area.get("areaDesc")

                    if "geocode" in area:
                        area_data["type"] = "geocode_block"
                        geocode = area.get("geocode")
                        geocode_data = {
                            "areaDesc": areaDesc,
                        }
                        if "valueName" in geocode:
                            geocode_data["valueName"] = geocode["valueName"]
                        if "value" in geocode:
                            geocode_data["value"] = geocode["value"]

                        area_data["value"] = geocode_data

                    if "polygon" in area:
                        area_data["type"] = "polygon_block"
                        polygon_data = {
                            "areaDesc": areaDesc,
                        }
                        geometry = area.get("geometry")
                        polygon_data["polygon"] = json.dumps(geometry)

                        area_data["value"] = polygon_data

                    if "circle" in area:
                        area_data["type"] = "circle_block"
                        circle_data = {
                            "areaDesc": areaDesc,
                        }
                        circle = area.get("circle")
                        # take the first circle for now
                        # TODO: handle multiple circles ? Investigate use case
                        circle_data["circle"] = circle[0]
                        area_data["value"] = circle_data

                    areas_data.append(area_data)

            stream_item = {
                "type": "alert_info",
                "value": {
                    **info_base_data,
                    "area": areas_data,
                },
            }

            info_blocks.append(stream_item)

    if title:
        base_data["title"] = title
        new_cap_alert_page = CapAlertPage(**base_data, live=False)
        new_cap_alert_page.info = StreamValue(
            new_cap_alert_page.info.stream_block, info_blocks, is_lazy=True)

        cap_list_page = HomePage.objects.live().first()

        if cap_list_page:
            cap_list_page.add_child(instance=new_cap_alert_page)
            cap_list_page.save_revision()

            messages.success(request, gettext(
                "CAP Alert draft created. You can now edit the alert."))

            return redirect(reverse("wagtailadmin_pages:edit", args=[new_cap_alert_page.id]))

    return None


@hooks.register("register_icons")
def register_icons(icons):
    return icons + [
        'cap/icons/category.svg',
        'cap/icons/certainty.svg',
        'cap/icons/clock.svg',
        'cap/icons/language.svg',
        'cap/icons/response.svg',
        'cap/icons/warning.svg',
    ]
