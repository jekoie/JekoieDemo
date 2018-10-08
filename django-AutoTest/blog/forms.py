from django import forms
from ckeditor_uploader.widgets import CKEditorUploadingWidget
from .models import Article

class SearchForm(forms.Form):
    search = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder':'搜索'}), required=False, empty_value='')

class CreateArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ['title', 'body']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'body': CKEditorUploadingWidget(attrs={'class': 'form-control'}, config_name='front')
        }

