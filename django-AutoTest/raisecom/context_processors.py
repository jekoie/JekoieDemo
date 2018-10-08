from autotest.models import AutoSoftModel

def autotest_version(request):
    obj = AutoSoftModel.objects.get(softname='AutoTest')

    return {'ver': obj}