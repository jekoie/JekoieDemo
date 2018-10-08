from django.urls import path
from . import views

app_name = 'blog'
urlpatterns = [
    path('diary/', views.diary_list, name='diary_list'),
    path('diary/collect/', views.diary_collect_list, name='diary_collect_list'),
    path('diary/detail/<int:id>/', views.diary_detail, name='diary_detail'),
    path('diary/create/<int:id>/', views.create_diary, name='create_diary'),
    path('diary/remove/<int:id>/', views.remove_diary, name='remove_diary'),
    path('diary/publish/<int:id>/<status>/', views.publish_diary, name='publish_diary'),
    path('blog/', views.blog_list, name='blog_list'),
    path('blog/<username>/', views.blog_list, name='blog_user_list'),
    path('blog/detail/<int:id>', views.blog_detail, name='blog_detail'),
    path('blog_like/', views.blog_like, name='blog_like'),
]