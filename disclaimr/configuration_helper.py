""" Functions to help with building the milter configuration """

from disclaimrwebadmin import models


def build_configuration():

    configuration = {
        "sender_ip": []
    }

    # Fetch the sender_ip networks of all enabled requirements, that have at least one enabled action in their associated rule

    for requirement in models.Requirement.objects.all():

        if requirement.enabled:

            # Check, if all associated actions are enabled

            enabled_actions = requirement.rule.action_set.count()

            for test_action in requirement.rule.action_set.all():

                if not test_action.enabled:

                    enabled_actions -= 1

            if enabled_actions > 0:

                # There are some enabled actions.

                configuration["sender_ip"].append({

                    "ip": requirement.get_sender_ip_network(),
                    "id": requirement.id

                })

    return configuration



