from django.urls import path
from . import views

app_name = 'autotest'
urlpatterns = [
    path('list/', views.show_sn, name='show_sn'),
    path('detail/', views.sn_detial, name='sn_detail'),
    path('softdown/', views.softdown, name='softdown'),
    path('website/', views.website, name='website'),
    path('ftp/<path:curdir>/<filetype>/', views.ftp, name='ftp'),
    path('ftp/', views.ftp, name='ftp_index'),
]