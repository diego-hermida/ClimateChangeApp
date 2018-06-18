from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls import handler403, handler404, handler500

from .settings import DEBUG, STATIC_ROOT, STATIC_URL

urlpatterns = [
    url(r'^management/', admin.site.urls),
    url(r'^', include('climate.urls'))
] + static(STATIC_URL, document_root=STATIC_ROOT)

if DEBUG:
    import debug_toolbar

    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += [url(r'^__debug__/', include(debug_toolbar.urls))]


handler403 = 'climate.views.error_403_view'
handler404 = 'climate.views.error_404_view'
handler500 = 'climate.views.error_500_view'
