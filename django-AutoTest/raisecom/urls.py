"""raisecom URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from instruction.views import  show_instruction
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', show_instruction),
    path('admin/', admin.site.urls),
    path('instruction/', include('instruction.urls')),
    path('autotest/', include('autotest.urls')),
    path('accounts/', include('accounts.urls')),
    path('admin/doc/',include('django.contrib.admindocs.urls')),
    path('ckedtior/', include('ckeditor_uploader.urls')),
    path('article/', include('blog.urls')),
    path('comments/', include('django_comments.urls')),
    path('pcomments/', include('comments.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400  = 'raisecom.views.handler400'
handler403  = 'raisecom.views.handler403'
handler404  = 'raisecom.views.handler404'
handler500 = 'raisecom.views.handler500'
