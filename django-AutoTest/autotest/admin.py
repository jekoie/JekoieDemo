from django.contrib import admin
from django.utils.html import  format_html
from easy_thumbnails.fields import  ThumbnailerImageField
from easy_thumbnails.widgets import  ImageClearableFileInput
from . import models
# Register your models here.

class SNModelAdmin(admin.ModelAdmin):
    fieldsets = [('其他字段', {
        'fields':  ['sn', 'segment1' , 'segment3' ,'segment4' , 'segment2' ,'result',
                    'operator', 'workorder', 'bomcode', 'productname', 'productver', 'lotno',
                    'starttime', 'endtime','totaltime'],
        'classes': ('collapse', 'wide')
    }),
                 (None, {
                     'fields': ('logserial', 'logprocess'),
                     'classes': ('wide', )
                 })
                 ]
    list_filter = ('result',)
    readonly_fields = ['logserial', 'logprocess', 'sn', 'segment1' , 'segment3' ,'segment4' , 'segment2' ,'result',
                       'operator', 'workorder', 'bomcode', 'productname', 'productver', 'lotno', 'starttime', 'endtime','totaltime']
    actions = None
    list_display = [ 'sn', 'segment1' ,'result', 'starttime','totaltime','operator','workorder', 'productname','productver']
    search_fields = ('sn', 'segment1', 'segment2', 'operator', 'workorder', 'productname')


class AutoSoftModelAdmin(admin.ModelAdmin):
    list_display = ['softname', 'author', 'version', 'path']
    fields = ['softname', 'author', 'version', 'path']
    readonly_fields = ['softname']
    actions = None
    save_as = False
    save_as_continue = False


class SoftwareModelAdmin(admin.ModelAdmin):
    list_display = ['softname', 'softtype', 'created', 'updated', 'download_counts']
    readonly_fields = ['download_counts']


class WebsiteModelAdmin(admin.ModelAdmin):
    list_display = ['name', 'url', 'image_photo', 'description']

    formfield_overrides = {
        ThumbnailerImageField : {'widget': ImageClearableFileInput},
    }

    def image_photo(self, obj):
        try:
            image_html = format_html('<img src="{}" height="30" width="30" />', obj.image.url)
        except Exception as e:
            return None

        return image_html
    image_photo.short_description = '图像'


admin.site.register(models.SNModel, SNModelAdmin)
admin.site.register(models.AutoSoftModel, AutoSoftModelAdmin)
admin.site.register(models.SoftwareModel, SoftwareModelAdmin)
admin.site.register(models.Website, WebsiteModelAdmin)