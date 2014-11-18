from django import forms
from django.contrib import admin
from django.forms import PasswordInput
from grappelli.forms import GrappelliSortableHiddenMixin
from .models import Rule, Requirement, Action, Disclaimer, DirectoryServer, \
    DirectoryServerURL


class RequirementInline(admin.StackedInline):

    model = Requirement
    extra = 0
    inline_classes = ('grp-collapse grp-open',)


class ActionInline(GrappelliSortableHiddenMixin, admin.StackedInline):

    model = Action
    extra = 0
    inline_classes = ('grp-collapse grp-open',)


class DirectoryServerURLInline(
    GrappelliSortableHiddenMixin,
    admin.TabularInline
):

    model = DirectoryServerURL
    extra = 0
    min_num = 1


@admin.register(Rule)
class RuleAdmin(admin.ModelAdmin):

    inlines = [
        RequirementInline,
        ActionInline
    ]


@admin.register(Disclaimer)
class DisclaimerAdmin(admin.ModelAdmin):

    class Media:

        js = [

            "//tinymce.cachefly.net/4.1/tinymce.min.js",
            "/static/tinymce_setup.js"

        ]


class DirectoryServerForm(forms.ModelForm):

    class Meta:

        model = DirectoryServer
        fields = "__all__"

        widgets = {

            "password": PasswordInput()

        }


@admin.register(DirectoryServer)
class DirectoryServerAdmin(admin.ModelAdmin):

    form = DirectoryServerForm

    inlines = [
        DirectoryServerURLInline
    ]
