from django.contrib import admin
from django_comments.moderation import CommentModerator, moderator
from .models import Article
# Register your models here.

class CollectionInlineAdmin(admin.TabularInline):
    model = Article.collect.through
    classes = ['collapse']

class ArticleModelAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'status', 'created')
    readonly_fields =  ('likes', 'reads')
    inlines = [CollectionInlineAdmin]

class ArticleModerator(CommentModerator):
    auto_close_field = 'published'
    close_after = 1


# moderator.register(Article, ArticleModerator)
admin.site.register(Article, ArticleModelAdmin)
