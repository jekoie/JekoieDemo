from django.db import models
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import ugettext_lazy as _
from .models import User
from .forms import GroupAdminForm
from easy_thumbnails.fields import ThumbnailerImageField
from easy_thumbnails.widgets import ImageClearableFileInput
from django.utils.html import  format_html
from django.contrib.auth.models import Group
# Register your models here.

class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'phone' ,'chinese_name', 'iamge_photo')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('chinese_name', 'email', 'phone', 'photo', 'addr')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'phone', 'email'),
        }),
    )
    formfield_overrides = {
        ThumbnailerImageField: {'widget': ImageClearableFileInput},
    }

    def iamge_photo(self, obj):
        try:
            image_html = format_html('<img  src="{}" size="30" width="30"/>'.format(obj.photo.url))
        except Exception as e:
            return None
        return image_html

    iamge_photo.short_description = '图像'

admin.site.register(User, UserAdmin)

#组模型
class GroupAdmin(admin.ModelAdmin):
    form = GroupAdminForm
    filter_horizontal = ['permissions']

admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)