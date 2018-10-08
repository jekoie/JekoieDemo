from django.db import models
from django_comments.abstracts import CommentAbstractModel, COMMENT_MAX_LENGTH
from django.contrib import admin
from django.utils.text import Truncator

class CommentModel(CommentAbstractModel):
    comment = models.TextField('评论', max_length=COMMENT_MAX_LENGTH)

    class Meta(CommentAbstractModel.Meta):
        ordering = ('-submit_date',)
        verbose_name = '评论'
        verbose_name_plural =  verbose_name


class CommentModelAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'user_email' , 'user_comment' ,'submit_date']
    readonly_fields = ['content_object', 'content_type' , 'site', 'object_pk']
    search_fields = ['user_name', 'user_comment']
    list_filter = ['user_name', 'user_email']
    def user_comment(self, obj):
        return Truncator(obj.comment).words(50)

    user_comment.short_description = '评论'


admin.site.register(CommentModel, CommentModelAdmin)