from django.urls import path
from . import views

app_name = 'comments'
urlpatterns = [
    path('delete/<int:comment_id>/', views.delete_own_comment, name='delete_own_comment'),
]

