from django.urls import path
from . import views

app_name = 'instruction'
urlpatterns = [
    path('', views.show_instruction,  name='show_instruction'),
    path('config_ins/', views.show_config_ins, name='show_config_ins'),
    path('config_index/', views.show_config_index, name='show_config_index')
]