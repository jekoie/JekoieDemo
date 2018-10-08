from django.shortcuts import render


def handler400(request, exception, template_name=''):
    return render(request, 'raisecom/400.html', status=400)

def handler403(request, exception, template_name=''):
    return render(request, 'raisecom/403.html', status=403)

def handler404(request, exception, template_name=''):
    return render(request, 'raisecom/404.html', status=404)

def handler500(request, exception, template_name=''):
    return render(request, 'raisecom/500.html', status=500)