from django.conf.urls import patterns, include, url
from django.contrib import admin

urlpatterns = patterns(
    '',
    (r'^grappelli/', include('grappelli.urls')),
    url(r'', include(admin.site.urls)),
)
