from django.shortcuts import render
from lxml import etree
from django.contrib.auth.decorators import permission_required
# Create your views here.

def show_instruction(request):
   return render(request, 'instruction/ins.html')

@permission_required('accounts.can_view')
def show_config_ins(request):
    return  render(request, 'instruction/config_ins.html')

def show_config_index(request):
    config_index = "ftp://192.168.60.70/AutoTest-Config/config.xml"
    parser = etree.XMLParser(encoding='utf-8', remove_blank_text=True )
    root = etree.parse(config_index, parser=parser).getroot()
    sum_list = {}
    total = 0
    current_name = ''
    for node in root.iterchildren():
        if node.__class__.__name__ == '_Comment':
            current_name = node.text
            sum_list[node.text] = {'count':0, 'child':[], 'nchild':[]}
        elif node.__class__.__name__ == '_Element':
            if len(node) == 0:
                total += 1
                sum_list[current_name]['count'] += 1
                sum_list[current_name]['child'].append(node)
            else:
                total += len(node)
                sum_list[current_name]['count'] += len(node)
                sum_list[current_name]['nchild'].append(node)

    return render(request, 'instruction/config_index.html', {'sum_list':sum_list, 'total': total})