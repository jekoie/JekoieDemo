#coding:utf-8
from lxml import etree
import feature

parser_without_comments = etree.XMLParser(encoding='utf-8', remove_blank_text=True, remove_comments=True)

def get_serial_setting_by_name(filepath, name):
    root = etree.parse(filepath, parser_without_comments).getroot()
    node = root.find('./port[@name="{}"]'.format(name))
    setting_value = feature.ParseSeqXML.get_element_dict(node)
    return setting_value


def tostr(obj):
    converted_obj = None
    if isinstance(obj, unicode):
        converted_obj = str(obj)
    elif isinstance(obj, dict):
        converted_obj = {str(k):str(v) for k,v in obj.iteritems()}

    return converted_obj if converted_obj else obj