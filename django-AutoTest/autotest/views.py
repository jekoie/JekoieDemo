import codecs
import csv
from django.shortcuts import render, redirect, reverse
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_POST
from .decorators import ajax_required
from django.utils import timezone
from openpyxl import Workbook
from django.http import FileResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from datetime import timedelta
from .  import models
from . import forms
import posixpath
import mimetypes
import io
from dateutil.parser import parse as dateparse
from .ftp import RFTP

FTP = RFTP()
# Create your views here.
#
def show_sn(request):
    if request.method == 'POST':
        form = forms.SNForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            sn_objs = models.SNModel.objects.defer('logserial', 'logprocess').filter(starttime__gte=cd['starttime'],
                                                    endtime__lte=cd['endtime'] + timedelta(days=1),
                                                    sn__icontains=cd['sn'], segment1__icontains=cd['mac'],
                                                    operator__icontains=cd['operator'], workorder__icontains=cd['workorder'],
                                                    productname__icontains=cd['productname'],
                                                    result__icontains='' if cd['result'] == 'ALL' else cd['result'])
            if sn_objs:
                if request.POST.get('csv') == 'csv' or request.POST.get('excel') == 'excel':
                    filename = timezone.now().strftime('{}_%Y%m%d'.format(request.user.username))
                    columns = ['SN', 'MAC', '线体', '结果', '起始时间', '结束时间', '测试时间', '操作员', '工单号', 'BOM编码', '产品名称', '产品版本', '物料代码', '批次号']
                    data = sn_objs.values_list('sn', 'segment1', 'segment4', 'result', 'starttime', 'endtime', 'totaltime', 'operator', 'workorder', 'bomcode', 'productname', 'productver', 'segment2', 'lotno')
                    if request.POST.get('csv') == 'csv':
                        response = HttpResponse(content_type='text/csv')
                        response.write(codecs.BOM_UTF8)
                        response['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(filename)
                        writer = csv.writer(response)
                        writer.writerow(columns)
                        for row_data in data:
                            writer.writerow(row_data)
                        return response
                    elif request.POST.get('excel') == 'excel':
                        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                        response['Content-Disposition'] = 'attachment; filename="{}.xlsx"'.format(filename)
                        wb = Workbook()
                        sheet = wb.active
                        sheet.append(columns)
                        for row_data in data:
                            sheet.append(row_data)
                        wb.save(response)
                        return response
                else:
                    pass_count = sn_objs.filter(result='PASS').count()
                    total_count = sn_objs.count()

                    qa = '{:.2%}'.format(pass_count / total_count)
                    data = sn_objs.values('id', 'sn', 'result', 'starttime', 'endtime', 'totaltime', 'operator',
                                          'bomcode', 'workorder','productname', 'productver', 'lotno', 'segment1', 'segment2', 'segment3','segment4')

                    return render(request, 'autotest/show_sn.html', { 'data': data, 'pass_count': pass_count, 'total_count': total_count, 'qa': qa, 'form': form})
            else:
                return render(request, 'autotest/show_sn.html', {'form': form})
    form = forms.SNForm()
    return render(request, 'autotest/show_sn.html', {'form': form})

@ajax_required
@require_POST
def sn_detial(request):
    ret = {}
    id = request.POST.get('id')
    infotype = request.POST.get('infotype')

    obj = models.SNModel.objects.get(id=id)
    ret['sn'] = obj.sn
    if infotype == 'serial':
        ret['log'] = obj.logserial
    elif infotype == 'process':
        ret['log'] = obj.logprocess
    else:
        ret['log'] = ''
    return JsonResponse(ret)


def softdown(request):
    if request.method == 'POST':
        id = request.POST.get('id', None)
        if id:
            soft = models.SoftwareModel.objects.get(pk=id)
            response = FileResponse(open(soft.file.path, 'rb') , content_type='application/octet-stream')
            response['Content-Disposition'] = 'attachment;filename="{}"'.format(soft.file.name)
            soft.download_counts += 1
            soft.save()
            return response

    autotest_softs = models.SoftwareModel.objects.filter(softtype='autotest')
    other_softs = models.SoftwareModel.objects.filter(softtype='other')
    return render(request, 'autotest/softdown.html', {'autotest_softs': autotest_softs, 'other_softs': other_softs})


def website(request):
    websites = models.Website.objects.all()
    return render(request, 'autotest/websites.html', {'websites': websites})

@login_required
@permission_required('accounts.can_view')
def ftp(request, curdir='.', filetype='folder'):
    ftp = FTP.get_ftp()
    if curdir == '.' : curdir = FTP.path
    if not curdir.startswith('/'): curdir = '/' + curdir
    if filetype == 'file':
        content_type = mimetypes.guess_type(curdir)[0]
        if content_type and 'text' in content_type:
            content_type += ';charset=utf8'

        ftp.chdir(posixpath.dirname(curdir))
        file = ftp.open(posixpath.basename(curdir), mode='rb')
        return HttpResponse(file, content_type=content_type)

    ftp.chdir(curdir)
    exit_document = ftp.listdir('')
    if request.method == 'POST' and request.POST:
        newname = request.POST.get('newname', None)
        oldname = request.POST.get('oldname', None)
        newfile_name = request.POST.get('newfile_name', None)
        newfolder_name = request.POST.get('newfolder_name', None)
        remove_files = request.POST.getlist('remove_files[]', None)
        if newfile_name and  newfile_name not in exit_document:       #新建文件
            try:
                ftp._session.storbinary('STOR {}'.format(newfile_name), io.BytesIO(b''))
                messages.success(request, '新建文件成功')
            except Exception as e:
                messages.error(request, '新建文件失败, {}'.format(e.args))
        elif newfolder_name and newfolder_name not in exit_document:   #新建文件夹
            try:
                ftp.mkdir(newfolder_name)
                messages.success(request, '新建文件夹成功')
            except Exception as e:
                messages.error(request, '新建文件夹失败, {}'.format(e.args))
        elif newname and oldname and oldname in exit_document:  #重命名
            try:
                ftp.rename(oldname, newname)
                messages.success(request, '重命名成功')
            except Exception as e:
                messages.error(request, '重命名失败, {}'.format(e.args))
        elif request.FILES:  #上传文件
            try:
                upload_file = request.FILES['upload']
                ftp._session.storbinary('STOR {}'.format(upload_file.name), upload_file)
                messages.success(request, '上传文件成功')
            except Exception as e:
                messages.error(request, '上传文件失败, {}'.format(e.args))
            return redirect(request.path)
        elif remove_files: #删除文件
            try:
                for remove_file in remove_files:
                    if remove_file in exit_document:
                        FTP.remove_file(remove_file)
                messages.success(request, '删除文件成功')
            except Exception as e:
                messages.error(request, '删除文件失败, {}'.format(e.args))

        return JsonResponse({'status': 'ok'})

    #获取父目录
    parent_dirs = []
    dr = FTP.path
    for dir in curdir.replace(FTP.path, 'home').split('/')[1:]:
        dr = posixpath.join(dr, dir)
        parent_dirs.append([dr, posixpath.basename(dr)])
    parent_dirs.insert(0, [FTP.path, 'home'])

    #获取文件信息
    form = forms.FTPUploadForm()
    files, dirs = {}, {}
    lines = []
    ftp._session.retrlines('MLSD', lines.append)
    for line in lines:
        words = line.split(';')
        if words[0] == 'Type=cdir':
            continue
        elif words[0] == 'Type=file':
            size = words[1].split('=')[1]
            mtime = dateparse( words[2].split('=')[1]  ) + timedelta(hours=8)
            files[words[-1].strip()] = {'size': size, 'mtime': mtime}
        elif words[0] == 'Type=dir':
            mtime = dateparse( words[1].split('=')[1]  )+ timedelta(hours=8)
            dirs[words[-1].strip()] = {'size': '-', 'mtime': mtime}

    return render(request, 'autotest/ftp.html', {'dirs': dirs, 'files': files, 'curdir': curdir, 'parent_dirs': parent_dirs, 'form': form})