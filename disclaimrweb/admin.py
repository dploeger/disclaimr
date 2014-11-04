from django.contrib import admin
from .models import Rule, Requirement, Action, Disclaimer


class RequirementInline(admin.StackedInline):

    model = Requirement
    extra = 0


class ActionInline(admin.StackedInline):

    model = Action
    extra = 0


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):

    inlines = [
        RequirementInline,
        ActionInline
    ]


@admin.register(Disclaimer)
class DisclaimerAdmin(admin.ModelAdmin):

    pass