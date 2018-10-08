from django import forms
from django.utils import timezone

class SNForm(forms.Form):
    sn = forms.CharField(label='SN', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    mac = forms.CharField(label='MAC', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    starttime = forms.DateField(label='起始时间', initial=timezone.now().date(), widget=forms.TextInput(attrs={'class': 'form-control datepicker'}))
    endtime = forms.DateField(label='结束时间', initial=timezone.now().date(), widget=forms.TextInput(attrs={'class': 'form-control datepicker'}))
    operator = forms.CharField(label='操作员', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    workorder = forms.CharField(label='工单号', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    productname = forms.CharField(label='产品名称', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    result = forms.ChoiceField(label='结果',initial='ALL' ,required=False, choices=[('ALL', 'ALL') , ('PASS', 'PASS'), ('FAIL', 'FAIL')],
                               widget=forms.Select(attrs={'class': 'form-control'}))


class FTPUploadForm(forms.Form):
    upload = forms.FileField(allow_empty_file=True)