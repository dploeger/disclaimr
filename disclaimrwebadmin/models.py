from django.db import models
from django.utils.translation import ugettext_lazy as _
import netaddr
import constants


class Rule(models.Model):

    """ A disclaimer rule.

        If all requirements are set, carry out the actions.
    """

    name = models.CharField(_("name"), max_length=255, help_text=_("The name of this rule."))
    description = models.TextField(_("description"), help_text=_("The description of this rule."), blank=True)

    def __unicode__(self):

        return self.name


class Requirement(models.Model):

    """ A disclaimer requirement.

        This describes various requirements, that need to be set for a disclaimer rule to work. If one requirement is set to
        deny, the complete rule will be denied (no actions will be carried out).

        One rule has to have at least one requirement to be taken into account during work.
    """

    rule = models.ForeignKey(Rule)

    name = models.CharField(_("name"), max_length=255, help_text=_("The name of this requirement."))

    description = models.TextField(_("description"), help_text=_("The description of this requirement."), blank=True)

    enabled = models.BooleanField(_("enabled"), default=True, help_text=_("Is this requirement enabled?"))

    sender_ip = models.GenericIPAddressField(_("sender-IP address"),
                                             help_text=_("A filter for the IP-address of the sender server."),
                                             default="0.0.0.0")
    sender_ip_cidr = models.CharField(_("netmask"), max_length=2, help_text=_("The CIDR-netmask for the sender ip address"),
                                      default="0")

    sender = models.TextField(_("sender"), help_text=_("A regexp, that has to match the sender of a mail."), default=".*")
    recipient = models.TextField(_("recipient"), help_text=_("A regexp, that has to match the recipient of a mail"),
                                 default=".*")

    header = models.TextField(_("header-filter"), help_text=_("A regexp, that has to match all headers of a mail. The headers "
                                                              "will be represented in a key: value - format."),
                              default=".*")
    body = models.TextField(_("body-filter"), help_text=_("A regexp, that has to match the body of a mail"), default=".*")

    action = models.SmallIntegerField(_("action"), help_text=_("What to do, if this requirement is met?"), choices=(
        (constants.REQ_ACTION_ACCEPT, _("Accept rule")),
        (constants.REQ_ACTION_DENY, _("Deny rule"))
    ), default=constants.REQ_ACTION_ACCEPT)

    class Meta:
        verbose_name = _("Requirement")

    def get_sender_ip_network(self):

        return netaddr.IPNetwork("%s/%s" % (self.sender_ip, self.sender_ip_cidr))

    def __unicode__(self):

        if not self.enabled:

            return _("%s (disabled)" % self.name)

        return self.name


class Disclaimer(models.Model):

    """ A disclaimer

        This is a text that gets inserted, added or otherwise handled in an action
    """

    name = models.CharField(_("name"), max_length=255, help_text=_("Name of this disclaimer"), default="")

    description = models.TextField(_("description"), help_text=_("A short description of this disclaimer"), default="",
                                   blank=True)

    text = models.TextField(_("text-part"), help_text=_("A plain text disclaimer"), default="", blank=True)

    text_use_template = models.BooleanField(_("use template tags"), help_text=_("Use template tags in the text part. Available "
                                                                                "tags are: {sender}, {recipient} and all "
                                                                                "attributes, that are provided by resolving the "
                                                                                "sender in a directory server"), default=True)

    html_use_text = models.BooleanField(_("use text part"), help_text=_("Use the contents of the text part for the html "
                                                                        "part."), default=True)

    html = models.TextField(_("html-part"), help_text=_("A html disclaimer (if not filled, the plain text disclaimer will be "
                                                        "used."), default="", blank=True)

    html_use_template = models.BooleanField(_("use template tags"), help_text=_("Use template tags in the html part. Available "
                                                                                "tags are: {sender}, {recipient} and all "
                                                                                "attributes, that are provided by resolving the "
                                                                                "sender in a directory server"),
                                            default=True)

    template_fail = models.BooleanField(_("fail if template doesn't exist"), help_text=_("Don't use this disclaimer (and stop "
                                                                                         "the associated action), "
                                                                                         "if a template tag cannot be "
                                                                                         "filled. If this is true, "
                                                                                         "the template tag will be replaced with "
                                                                                         "an empty string."), default=False)

    def __unicode__(self):

        return self.name


class DirectoryServer(models.Model):

    """ A directory server. This is used, if an action needs to resolve the user by the mail's recipient or sender
    """

    name = models.CharField(_("name"), max_length=255, help_text=_("The name of this action."))

    description = models.TextField(_("description"), help_text=_("The description of this action."), blank=True)

    enabled = models.BooleanField(_("enabled"), default=True, help_text=_("Is this directory server enabled?"))

    base_dn = models.CharField(_("base-dn"), max_length=255, help_text=_("The LDAP base dn."))

    auth = models.SmallIntegerField(_("auth-method"), help_text=_("Authentication method to connect to the server"), choices=(
        (constants.DIR_AUTH_NONE, _("None")),
        (constants.DIR_AUTH_SIMPLE, _("Simple"))
    ), default=constants.DIR_AUTH_NONE)

    userdn = models.CharField(_("user-DN"), max_length=255, help_text=_("DN of the user to authenticate with"), blank=True,
                              default="")

    password = models.CharField(_("password"), max_length=255, help_text=_("Password to authenticate with"), blank=True,
                                default="")

    search_query = models.TextField(_("search query"), help_text=_("A search query to run against the directory server to "
                                                                   "fetch the ldap object when resolving. %s will be "
                                                                   "replaced when resolving."),
                                    default="mail=%s")

    def __unicode__(self):

        if not self.enabled:

            return _("%s (disabled)" % self.name)

        return self.name


class DirectoryServerURL(models.Model):

    """ An URL for a directory server. One directory server configuration can have multiple URLs, which are used in turn,
    if the first isn't responding
    """

    directory_server = models.ForeignKey(DirectoryServer)

    url = models.CharField(_("URL"), max_length=255, help_text=_("URL of the directory server. For example: "
                                                                 "ldap://ldapserver:389/ or ldaps://ldapserver/"))

    position = models.PositiveSmallIntegerField(_("Position"))

    class Meta:
        ordering = ['position']
        verbose_name = _("URL")

    def __unicode__(self):

        return self.url


class Action(models.Model):

    """ A disclaimer action.

        This describes, what should be done with the mail meeting the requirements in a rule
    """

    rule = models.ForeignKey(Rule)
    position = models.PositiveSmallIntegerField(_("Position"))

    name = models.CharField(_("name"), max_length=255, help_text=_("The name of this action."))

    enabled = models.BooleanField(_("enabled"), default=True, help_text=_("Is this action enabled?"))

    description = models.TextField(_("description"), help_text=_("The description of this action."), blank=True)

    action = models.SmallIntegerField(_("action"), help_text=_("What action should be done?"), choices=(
        (constants.ACTION_ACTION_REPLACETAG, _("Replace a tag in the body with a disclaimer string")),
        (constants.ACTION_ACTION_ADD, _("Add a disclaimer string to the body")),
    ), default=constants.ACTION_ACTION_ADD)

    only_mime = models.CharField(_("mime type"), max_length=255, help_text=_("Only carry out the action in the given mime "
                                                                             "type"), default="", blank=True)

    action_parameters = models.TextField(_("action parameters"), help_text=_("Parameters for the action (see the action "
                                                                             "documentation for details)"), default="",
                                         blank=True)

    resolve_sender = models.BooleanField(_("resolve the sender"), help_text=_("Resolve the sender by querying a directory "
                                                                              "server and provide data for the template tags "
                                                                              "inside a disclaimer"), default=False)

    resolve_sender_fail = models.BooleanField(_("fail when unable to resolve sender"), help_text=_("Stop the action if the "
                                                                                                   "sender cannot be "
                                                                                                   "resolved."), default=False)

    disclaimer = models.ForeignKey(Disclaimer, help_text=_("Which disclaimer to use"))

    directory_servers = models.ManyToManyField(DirectoryServer, help_text=_("Which directory server(s) to use."))

    class Meta:
        ordering = ['position']
        verbose_name = _("Action")

    def __unicode__(self):

        if not self.enabled:

            return _("%s (disabled)" % self.name)

        return self.name
