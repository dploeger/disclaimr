from django.db import models
from django.utils.translation import ugettext_lazy as _

# DisclaimrWeb models


class Rule(models.Model):

    """ A disclaimer rule.

        If all requirements are set, carry out the actions.
    """

    name = models.CharField(_("name"), max_length=255, help_text=_("The name of this rule."))
    description = models.TextField(_("description"), help_text=_("The description of this rule."), blank=True)

    def __str__(self):

        return self.name


class Requirement(models.Model):

    """ A disclaimer requirement.

        This describes various requirements, that need to be set for a disclaimer rule to work
    """

    rule = models.ForeignKey(Rule)

    sender_ip = models.IPAddressField(_("sender-IP address"), help_text=_("A filter for the IP-address of the sender server."),
                                      default="0.0.0.0/0")
    sender = models.TextField(_("sender"), help_text=_("A regexp, that has to match the sender of a mail."), default="^.*$")
    recipient = models.TextField(_("recipient"), help_text=_("A regexp, that has to match the recipient of a mail"),
                                 default="^.*$")

    header = models.TextField(_("header-filter"), help_text=_("A regexp, that has to match all headers of a mail"),
                              default="^.*$")
    body = models.TextField(_("body-filter"), help_text=_("A regexp, that has to match the body of a mail"), default="^.*$")

    action = models.CharField(_("action"), max_length=30, help_text=_("What to do, if this requirement is met?"), choices=(
        ("ACCEPT", _("Accept rule")),
        ("DENY", _("Deny rule"))
    ), default="ACCEPT")


class Disclaimer(models.Model):

    """ A disclaimer

        This is a text that gets inserted, added or otherwise handled in an action
    """

    name = models.CharField(_("name"), max_length=255, help_text=_("Name of this disclaimer"), default="")

    description = models.TextField(_("description"), help_text=_("A short description of this disclaimer"), default="",
                                   blank=True)

    text = models.TextField(_("text-part"), help_text=_("A plain text disclaimer"), default="", blank=True)
    html = models.TextField(_("html-part"), help_text=_("A html disclaimer (if not filled, the plain text disclaimer will be "
                                                        "used."), default="", blank=True)

    def __str__(self):

        return self.name


class Action(models.Model):

    """ A disclaimer action.

        This describes, what should be done with the mail meeting the requirements in a rule
    """

    rule = models.ForeignKey(Rule)

    action = models.CharField(_("action"), max_length=30, help_text=_("What action should be done?"), choices=(
        ("REPLACETAG", _("Replace a tag in the body with a disclaimer string")),
        ("ADD", _("Add a disclaimer string to the body")),
    ), default="ADD")

    only_mime = models.CharField(_("mime type"), max_length=255, help_text=_("Only carry out the action in the given mime "
                                                                             "type"), default="", blank=True)

    action_parameters = models.TextField(_("action parameters"), help_text=_("Parameters for the action (see the action "
                                                                             "documentation for details"), default="", blank=True)

    disclaimer = models.ForeignKey(Disclaimer)