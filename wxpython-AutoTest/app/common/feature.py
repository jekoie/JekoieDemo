# coding=utf-8
from ..oracle import cx_Oracle
import pathlib
import wx
import wx.adv
import ftputil.error
import re
import os
import sys
import time
import wx.lib.dialogs
import serial
import serial.serialutil
import logging
import wx.lib.scrolledpanel as SP
import pypyodbc
import traceback
import httplib
import ftfy
from serial.tools.list_ports import comports as serial_comports
from wx.lib.pdfviewer import pdfViewer, pdfButtonPanel
from ftputil import sync
from toolz import itertoolz
from wx.html2 import WebView
import  wx.lib.mixins.listctrl  as  listmix
from wx.lib.pubsub import pub
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer
import threading
import socket
import wx.lib.filebrowsebutton as filebrowse
import ftputil
import wx.lib.agw.pybusyinfo as PBI
from lxml import etree
import posixpath
import uuid
import numpy
import pandas as pd
import wx.lib.newevent
import binascii
import io
import tftpy
import arrow
import common
from wx.py import shell
from wx.lib.splitter import MultiSplitterWindow


TOPIC_PORT_SET = 'TOPIC_PORT_SET'
COLOUR_RED = wx.Colour(249, 0, 0)
COLOUR_GREEN = wx.Colour(0, 249, 0)
COLOUR_YELLOW = wx.Colour(239, 249, 49)
COLOUR_WHITE = wx.Colour(255, 255, 255)
COLOUR_BLACK = wx.Colour(0, 0, 0)
COLOUR_GRAY = wx.Colour(127, 127, 127)
COLOUR_AQUA = wx.Colour(32,178,170)

PASS, FAIL, ERROR = 'PASS', 'FAIL', 'ERROR'
############################单串口版##############################

def errorencode(str):
    return unicode(str, encoding='gbk', errors='ignore')

def convert_value(value="", flag=[]):
    if 'upper' in flag:
        if value != None:
            value = value.upper()

    if 'lower' in flag:
        if value != None:
            value = value.lower()

    if 'lstrip' in flag:
        if value != None:
            value = value.lstrip()

    if 'rstrip' in flag:
        if value != None:
            value = value.rstrip()

    if 'strip' in flag:
        if value != None:
            value = value.strip()

    if "date" in flag:
        t = pd.to_datetime(value, errors='ignore')
        if t.__class__.__name__ == 'Timestamp':
            value = t.strftime('%Y%m%d')

    if 'length' in flag:
        if value != None:
            value = len(value)

    return value

def query_linestation_info(appconfig):
    mes_attr = appconfig['mes_attr']
    mes_cursor = appconfig['mes_cursor']
    workjob_sql = "select distinct workjob_code from DMSNEW.work_workjob where workjob_code='{}' ".format(mes_attr['extern_WJTableName'])
    line_sql = "select distinct linecode,line from DMSNEW.workproduce where linecode='{}' ".format(mes_attr['extern_SubLineCode'])
    station_sql = "select distinct code, name from DMSNEW.qa_mantaince_type where code='{}' ".format(mes_attr['extern_StationCode'])
    worksql_value = mes_cursor.execute(workjob_sql).fetchone()
    linesql_value = mes_cursor.execute(line_sql).fetchone()
    stasql_value = mes_cursor.execute(station_sql).fetchone()

    if worksql_value :
        worksql_flag = True
        #特殊评审说明
        review_sql = "select segment33 from DMSNEW.work_workjob  where workjob_code='{}' ".format(mes_attr['extern_WJTableName'])
        review_sql_value = mes_cursor.execute(review_sql).fetchone()
        mes_attr['workjob_review'] = review_sql_value[0] if review_sql_value[0] else str(uuid.uuid4())
        tipmsg = u'1.工单号：{}正确\n'.format(mes_attr['extern_WJTableName'])
    else:
        worksql_flag = False
        tipmsg = u'1.工单号：{}.不存在\n'.format(mes_attr['extern_WJTableName'])

    if linesql_value:
        linesql_flag = True
        tipmsg += u'2.线体：{}正确\n'.format(mes_attr['extern_SubLineCode'])
    else:
        linesql_flag = False
        tipmsg +=  u'2.线体：{}.不存在\n'.format( mes_attr['extern_SubLineCode'])

    if stasql_value:
        stasql_falg = True
        tipmsg += u'3.工序：{}正确\n'.format(mes_attr['extern_StationCode'])
    else:
        stasql_falg = False
        tipmsg += u'3.工序：{}.不存在\n'.format( mes_attr['extern_StationCode'])

    if mes_attr['op_workers'] <= 0:
        stasql_value = None
        tipmsg += u'4.投入人数需大于0\n'

    if stasql_value is not None and len(stasql_value) == 2:
        mes_attr['extern_StationName'] = stasql_value[1]

    appconfig['worktable_loaded'] = True if worksql_flag and linesql_flag and stasql_falg else False
    appconfig['worktable_had_changed'] = True if  appconfig['worktable_loaded'] else False
    return worksql_value, linesql_value, stasql_value, tipmsg


def getProductXML(ftp_base_dir_anonymous="ftp://192.168.60.70/AutoTest-Config/", subproduct="", sn=''):
    parser = etree.XMLParser(encoding='utf-8', remove_blank_text=True, remove_comments=True)
    config_xml_path = posixpath.join(ftp_base_dir_anonymous, "config.xml")
    comfig_tree = etree.parse(config_xml_path, parser)
    config_xml_root = comfig_tree.getroot()
    for item in config_xml_root.getchildren():
        sn_stigma = item.get('bom', '')
        if sn_stigma.upper() == sn[:len(sn_stigma)].upper():
            if len(item) == 0:
                xml_path_list = item.get('xml', '').split('/')[1:]
                xml_path = posixpath.join(ftp_base_dir_anonymous, *xml_path_list)
                product_name = item.get('product')
                return ParseSeqXML(xml_path), product_name
            else:
                default_value = review_value = None
                for subitem in item:
                    if subitem.get('review', str(uuid.uuid4()) ) in subproduct:
                        xml_path_list = subitem.get('xml', '').split('/')[1:]
                        xml_path = posixpath.join(ftp_base_dir_anonymous, *xml_path_list)
                        product_name = subitem.get('product', '')
                        review_value = ParseSeqXML(xml_path), product_name
                        break
                    elif 'default' in subitem.get('review', uuid.uuid4()):
                        xml_path_list = subitem.get('xml', '').split('/')[1:]
                        xml_path = posixpath.join(ftp_base_dir_anonymous, *xml_path_list)
                        product_name = subitem.get('product', '')
                        default_value = ParseSeqXML(xml_path), product_name

                if review_value is not None:
                    return  review_value
                elif default_value is not None:
                    return  default_value
                else:
                    return None, None
    return None, None

#sync server time to local
def time_sync():
    try:
        def set_time(date_str):
            gmt_time_struct = time.strptime(date_str[5:25], "%d %b %Y %H:%M:%S")
            ltime = time.localtime(time.mktime(gmt_time_struct) + 8 * 60 * 60)
            date_cmd = 'date {}-{}-{}'.format(ltime.tm_year, ltime.tm_mon, ltime.tm_mday)
            time_cmd = 'time {}:{}:{}'.format(ltime.tm_hour, ltime.tm_min, ltime.tm_sec)
            os.system(date_cmd)
            os.system(time_cmd)

        host = '192.168.60.70'
        conn = httplib.HTTPConnection(host=host, timeout=3)
        conn.request('GET', '/')
        resp = conn.getresponse()
        date_str = resp.getheader('date')
        threading.Thread(target=set_time, args=(date_str,)).start()
        return True
    except Exception as e:
        return False

def macAddrCreator(mac, count=100):
    mac_str = mac.replace(':', '')
    mac_num = int(mac_str, 16)
    mac_dict = {}
    for i in range(count):
        mac_str = hex(mac_num+i).upper().strip('0X').strip('L')
        mac_str = '{:0>12}'.format(mac_str)
        mac3_str = mac_str[0:4] + '.' + mac_str[4:8] + '.' + mac_str[8:]
        mac_str = ':'.join([ mac_str[j:j+2] for j in range(0, 12, 2)])
        mac_dict['@3MAC{}'.format(i)] = mac3_str
        mac_dict['@MAC{}'.format(i)] = mac_str
    return mac_dict


def inttomac(mac_int=0):
    mac_str = '{:0>12X}'.format(int(mac_int))
    return  ':'.join([mac_str[i:i+2] for i in xrange(0,12,2)] )

def macAddrCreatorForSlave(mac, prefix="slave1"):
    mac_str = mac.replace(':', '')
    mac_num = int(mac_str, 16)
    mac_dict = {}
    for i in range(50):
        mac_str = hex(mac_num+i).upper().strip('0X').strip('L')
        mac_str = '{:0>12}'.format(mac_str)
        mac3_str = mac_str[0:4] + '.' + mac_str[4:8] + '.' + mac_str[8:]
        mac_str = ':'.join([ mac_str[j:j+2] for j in range(0, 12, 2)])
        mac_dict['@slave13mac{}'.format(i)] = mac3_str
        mac_dict['@slave1mac{}'.format(i)] = mac_str
    return mac_dict

def getMacValue(window):
    # mac address verify
    mac_value = None
    mac_dlg = wx.TextEntryDialog(window, u'请输入产品MAC地址', u'{}:MAC Address'.format(window.name))
    mac_dlg.CentreOnParent()
    while True:
        if mac_dlg.ShowModal() == wx.ID_OK:
            mac_value = mac_dlg.GetValue().strip()
            if re.match(r'^([A-F\d]{2}:){5}([A-F\d]{2})$', mac_value, re.I):
                mac_dlg.Destroy()
                return True, mac_value.strip().upper()
            else:
                for childwin in mac_dlg.GetChildren():
                    if childwin.GetClassName() == 'wxStaticText':
                        childwin.SetLabelText(u'产品MAC地址输入有误，请重新输入')
                    if childwin.GetClassName() == 'wxTextCtrl':
                        childwin.SelectAll()
        else:
            mac_dlg.Destroy()
            return  False, mac_value


def get_bind_info_by_barcode(appconfig, sn_value):
    #(103002027500S17C28S0010D, C8:50:E9:6E:40:86, C8:50:E9:6E:40:87, )
    extern_WJTableName = appconfig['mes_attr']['extern_WJTableName']
    sql = "select DISTINCT barcode,MACMA, MACMA2,waima from dmsnew.{} where macma is not null and barcode = '{}' ".format(extern_WJTableName, sn_value)
    sql_value = appconfig['mes_cursor'].execute(sql).fetchone()
    return sql_value

def getBadCode(window, appconfig):
    # sn verify
    value = None
    mes_cursor = appconfig['mes_cursor']
    bad_dlg = wx.TextEntryDialog(window, u'请输入不良代码', u'{}:不良代码'.format(window))
    bad_dlg.CentreOnParent()
    while True:
        if bad_dlg.ShowModal() == wx.ID_OK:
            value = bad_dlg.GetValue().strip()
            sql_value = mes_cursor.execute("select name,bug_type,describe from DMSNEW.qa_bug_type where code='{}' ".format(value)).fetchall()
            if len(sql_value) != 0:
                badname =  mes_value(sql_value[0][0])
                badtype =  mes_value(sql_value[0][1])
                baddesc = mes_value(sql_value[0][2])
                bad_dlg.Destroy()
                return True, (badname, badtype, baddesc)
            else:
                for childwin in bad_dlg.GetChildren():
                    if childwin.GetClassName() == 'wxStaticText':
                        childwin.SetLabelText(u'不良代码输入有误，请重新输入')
                    if childwin.GetClassName() == 'wxTextCtrl':
                        childwin.SelectAll()
        else:
            bad_dlg.Destroy()
            return False, value

def getSpecialMac(window, title):
    mac_value = None
    mac_dlg = wx.TextEntryDialog(window, u'{}'.format(title), 'MAC')
    while True:
        if mac_dlg.ShowModal() == wx.ID_OK:
            mac_value = mac_dlg.GetValue().strip().upper()
            if re.match(r'^([A-F\d]{2}:){5}([A-F\d]{2})$', mac_value, re.I):
                mac_dlg.Destroy()
                return True, mac_value
            else:
                for childwin in mac_dlg.GetChildren():
                    if childwin.GetClassName() == 'wxStaticText':
                        childwin.SetLabelText(u'产品MAC地址输入有误，请重新输入')
                    if childwin.GetClassName() == 'wxTextCtrl':
                        childwin.SelectAll()
        else:
            mac_dlg.Destroy()
            return False, mac_value


def getWorkstageMsgBox(window, item_attr):
    msg, caption = item_attr.get('msg', ''), item_attr.get('caption', '')
    initial_value, type = item_attr.get('initial_value', ''),  item_attr.get('type', 'msgbox')
    name, show = item_attr.get('name', '@WORKSTAGE_MSGBOX'), item_attr.get('show', 'True')
    flag = item_attr.get('flag', '').split('|')
    if show not in "True":
        return True, {name: initial_value}

    dlg = wx.TextEntryDialog(window, msg, '{}:{}'.format(window.name, caption), initial_value, style=wx.OK)
    dlg.CentreOnParent()
    if type in 'msgbox':
        while True:
            if dlg.ShowModal() == wx.ID_OK and dlg.GetValue() != '':
                value = convert_value(dlg.GetValue(), flag)
                dlg.Destroy()
                return True, {name:value}
            # else:
            #     dlg.Destroy()
            #     return False, {}

def getWorkstage(window, xml):
    msg = ''
    candidate_value_list = []
    workstage_ele = xml.root.find('.//workstage')
    if workstage_ele is None: return True, None
    for child in workstage_ele.iterchildren():
        msg += child.get('name', '') + '\n'
        candidate_value_list.append(child.get('value', 'unchoosed'))
    workstage_dlg = wx.TextEntryDialog(window, u'{}'.format(msg.rstrip()), u'{}:工序选择'.format(window.name))
    workstage_dlg.CentreOnParent()
    while True:
        if workstage_dlg.ShowModal() == wx.ID_OK:
            workstage_value = workstage_dlg.GetValue().strip()
            if workstage_value in candidate_value_list:
                workstage_dlg.Destroy()
                return True, workstage_value
            else:
                for childwin in workstage_dlg.GetChildren():
                    if childwin.GetClassName() == 'wxStaticText':
                        workstage_dlg.SetTitle(u'工序选择错误' )
                    if childwin.GetClassName() == 'wxTextCtrl':
                        childwin.SelectAll()
        else:
            workstage_dlg.Destroy()
            return False, None

def getSNValue(window):
    # sn verify
    sn_value = None
    sn_dlg = wx.TextEntryDialog(window, u'请输入产品SN', u'{}:SN'.format(window.name))
    sn_dlg.CentreOnParent()
    while True:
        if sn_dlg.ShowModal() == wx.ID_OK:
            sn_value = sn_dlg.GetValue().strip()
            if re.match(r'^[A-Z0-9-_]+', sn_value, re.I):
                sn_dlg.Destroy()
                return True, sn_value.strip().upper()
            else:
                for childwin in sn_dlg.GetChildren():
                    if childwin.GetClassName() == 'wxTextCtrl':
                        childwin.SelectAll()
        else:
            sn_dlg.Destroy()
            return False, sn_value

def mes_value(value):
    mes_value =  '' if value == None else  ftfy.fix_text( unicode(value) )
    return mes_value

def handy_sync_dir(remote_dir, local_dir):
    with sync.FTPHost('192.168.60.70', 'anonymous', 'anonymous') as remote:
        local = sync.LocalHost()
        syncer = sync.Syncer(remote, local)
        syncer.sync(remote_dir, local_dir)

def auto_sync_dir(remote_dir, local_dir):
    with ftputil.FTPHost('192.168.60.70', 'anonymous', 'anonymous') as remote:
        for dirpath, dirnames, filenames in remote.walk(remote_dir):
            for filename in filenames:
                remote_file = pathlib.PurePosixPath(dirpath, filename)
                local_file = pathlib.PureWindowsPath(remote_file.as_posix().replace(remote_dir, local_dir) )
                if not os.path.exists(local_file.parent.as_posix()):
                    os.makedirs(local_file.parent.as_posix())
                remote.download_if_newer(remote_file.as_posix(), local_file.as_posix() )

def generate_setting_file(settingfile):
    if not os.path.exists(settingfile):
        rootElement = etree.Element('root')
        for i in range(0, 100):
            attrib = { 'name':'COM{}'.format(i), 'baudrate':'9600', 'bytesize':'8' ,'stopbits':'1',
                       'parity':'N' , 'timeout':'0', 'write_timeout':'0' , 'enable':"True"}
            etree.SubElement(rootElement, 'port', attrib)

        with open(settingfile, 'wb') as f:
            f.write(etree.tostring(rootElement, pretty_print=True, encoding='utf-8', xml_declaration=True) )
    # print etree.tostring(rootElement, pretty_print=True, encoding='utf-8', xml_declaration=True)

def generate_config_file(settingdir, configxml):
    rootElement = etree.Element('root')
    for dirpath, dirnames, filenames in os.walk(settingdir):
        if dirpath == settingdir: continue
        dir_segment =  dirpath.replace(settingdir, '', 1)
        dir_segment = dir_segment.split('\\')
        dir_segment_len = len(dir_segment)
        if dir_segment_len == 2 and 'config.xml' in filenames:
            config_file = os.path.join(dirpath, 'config.xml')
            parser = etree.XMLParser(encoding='utf-8', remove_blank_text=True, remove_comments=True)
            tree = etree.parse(config_file, parser)
            comment = etree.Comment(itertoolz.last(dir_segment) )
            rootElement.append(comment)
            for item  in tree.iter(tag='li'):
                item.attrib['xml'] = item.attrib['xml'][:2] + itertoolz.last(dir_segment) + '/' + item.attrib['xml'][2:]
                etree.SubElement(rootElement, item.tag, item.attrib)

    with open(configxml, 'wb') as f:
        f.write(etree.tostring(rootElement, encoding='utf-8', xml_declaration=True, pretty_print=True) )


def update_config_file(ftp_config_base_dir=u"工艺工作文件夹/工艺资料/AutoTest-Config", local_setting_file="./setting/config.xml" ):
    #更新提示信息
    msg, ret_status = '', True
    busy = PBI.PyBusyInfo(u'正在更新配置', None, u'更新')
    wx.GetApp().Yield()
    basedir = ftp_config_base_dir
    rootElement = etree.Element('root')
    parser = etree.XMLParser(encoding='utf-8', remove_blank_text=True, remove_comments=True)
    ftp = ftputil.FTPHost("192.168.60.70", "szgy-chenjie", "szgy-chenjie")
    ftp.chdir(basedir.encode("gbk"))
    for dirpath, dirnames, filenames in ftp.walk("."):
        try:
            dirpath_seg = dirpath.split("/")
            dirpath_seg_len = len(dirpath_seg)
            if dirpath_seg_len == 2 and 'config.xml' in filenames:
                config_file = posixpath.join(dirpath, 'config.xml')
                config_file_handle = ftp.open(config_file, encoding="utf-8")
                tree = etree.parse(config_file_handle, parser)
                comment = etree.Comment(dirpath_seg[-1])
                rootElement.append(comment)
                for item in tree.xpath('./li'):
                    if len(item) == 0:
                        xml_path = item.get('xml', '')
                        item.attrib['xml'] = xml_path[:2] + dirpath_seg[-1] + '/' + xml_path[2:]
                        etree.SubElement(rootElement, item.tag, item.attrib)
                    else:
                        for subitem in item:
                            xml_path = subitem.get('xml', '')
                            subitem.attrib['xml'] = xml_path[:2] + dirpath_seg[-1] + '/' + xml_path[2:]
                        rootElement.append(item)
        except Exception as e:
            msg += '文件：{} 错误：{}\n'.format(config_file, e.message)
            ret_status = False
            continue

    with open(local_setting_file, mode="w",) as f:
        f.write(etree.tostring(rootElement, xml_declaration=True, pretty_print=True, encoding="utf-8"))

    ftp.upload(local_setting_file, "./config.xml")
    ftp.close()
    del busy

    return msg, ret_status

def getMesVar(mes_attr, mes_cursor):
    mes_attr['@MES_PRODUCTTYPE'] = mes_attr['extern_stritemtype']
    mes_attr['@MES_LOTNO'] = mes_attr['extern_lotno']
    mes_attr['@MES_CUSTOMER_PRODUCTNAME'] = mes_attr['extern_mytype']
    mes_attr['@MES_PRODUCTNAME'] = mes_attr['extern_stritemmemo']

def assignMesAttr(appconfig):
    mes_attr = appconfig['mes_attr']
    mes_cursor = appconfig['mes_cursor']
    extern_WJTableName = mes_attr['extern_WJTableName']
    extern_StationCode = mes_attr['extern_StationCode']

    sql = "select serial_number,sub_attempter_code,attempter_code,order_code,class," + \
          " to_char(attemper_begin_date,'yyyy-mm-dd hh24:mi:ss') attemper_begin_date,to_char(attemper_end_date,'yyyy-mm-dd hh24:mi:ss') attemper_end_date," + \
          "worksubsequence_code,workshop,work_code,line_code,worksations,persons, number1,number2,ympk,yinum,oddscan,work_code2,testposition," + \
          "decode(bug_num,0,'否',1,'是','是') bug_num,TOTALSENDNUM from DMSNEW.mtl_sub_attemper where  state in('已调度' , '已开工') "
    sql += " and  order_code='{}' and TESTPOSITION in ( select name from DMSNEW.qa_mantaince_type  where code='{}' )".format(extern_WJTableName, extern_StationCode)

    sql_value = mes_cursor.execute(sql).fetchall()
    if len(sql_value) == 0:
        appconfig['worktable_loaded'] = False
        return False, u'此调度单为空'

    mes_attr['extern_SerialNumber'] = mes_value(sql_value[0][0])
    mes_attr['extern_SubAttemperCode'] = mes_value(sql_value[0][1])
    mes_attr['extern_AttempterCode'] = mes_value(sql_value[0][2])
    mes_attr['extern_strympk'] = mes_value(sql_value[0][15])
    mes_attr['extern_Num1'] = mes_value(sql_value[0][16])
    mes_attr['extern_SubTestPosition'] = mes_value(sql_value[0][19])
    mes_attr['extern_strWorkCode2'] = mes_value(sql_value[0][18])
    # mes_attr['op_workers'] = mes_value(sql_value[0][21])
    mes_attr['extern_strmpk'] = '0'


    sql = "select item_code,item_version,item_type ,item_memo, lotno, segment17,segment11,mytype,item_num  from DMSNEW.work_workjob where workjob_code='{}'".format(extern_WJTableName)
    sql_value = mes_cursor.execute(sql).fetchall()
    # 产品编码
    mes_attr['extern_stritemcode'] = mes_attr['extern_productcode'] = mes_value(sql_value[0][0])
    # 产品版本
    mes_attr['extern_stritemversion'] = mes_attr['extern_productversion']= mes_value(sql_value[0][1])
    # 规格型号
    mes_attr['extern_stritemtype'] =  mes_attr['extern_producttype'] = mes_value(sql_value[0][2])
    # 产品名称
    mes_attr['extern_stritemmemo'] =  mes_attr['extern_productname'] = mes_value(sql_value[0][3])
    # 计划模式
    mes_attr['extern_plan_mode'] = mes_value(sql_value[0][6])
    # 客户产品型号
    mes_attr['extern_mytype'] = mes_value(sql_value[0][7])
    mes_attr['extern_lotno'] = mes_value(sql_value[0][4])
    mes_attr['extern_bomcode'] = mes_value(sql_value[0][5])
    #item_num任务单 SN数量
    mes_attr['extern_Num1'] = mes_attr['extern_item_num'] = mes_value(sql_value[0][8])

    extern_SubLineCode = mes_attr['extern_SubLineCode']
    sql = "select line,workshopname,biglinename from DMSNEW.workproduce where linecode='{}' ".format(extern_SubLineCode)
    sql_value = mes_cursor.execute(sql).fetchall()
    mes_attr['extern_SubLine'] = mes_value(sql_value[0][0])
    mes_attr['extern_workshopname'] = mes_value(sql_value[0][1])
    mes_attr['extern_biglinename'] = mes_value(sql_value[0][2])

    appconfig['worktable_loaded'] = True
    getMesVar(mes_attr, mes_cursor)

    return True, ''

#查询可用SN记录
def get_available_sn(appconfig):
    mes_cursor = appconfig['mes_cursor']
    extern_WJTableName = appconfig['mes_attr']['extern_WJTableName']
    extern_SerialNumber =  appconfig['mes_attr']['extern_SerialNumber']
    sql = "select barcode from ((select barcode from  dmsnew.{worktable}  where scan_position='L' and" \
          " qulity_flag ='no' and scan_type='正常生产' and segment13 ='no'  and subid =({extern_SerialNumber}-1)) minus " \
          "(select barcode from dmsnew.{worktable} where scan_position='L' and  qulity_flag ='no' and scan_type ='正常生产' " \
          "and segment13 ='no' and subid={extern_SerialNumber} ))".format(worktable=extern_WJTableName, extern_SerialNumber=extern_SerialNumber)
    sql_value = mes_cursor.execute(sql).fetchall()

    available_sn_list = []
    for available_sn in sql_value:
        available_sn_list.append(available_sn[0])

    return available_sn_list

#记录MES查询记录
def record_mes_query(appconfig):
    try:
        mes_attr = appconfig['mes_attr']
        workjob_code = mes_attr['extern_WJTableName']
        item_code = mes_attr['extern_productcode']
        item_type = mes_attr['extern_producttype']
        line_code = mes_attr['extern_SubLine']
        testposition = mes_attr['extern_SubTestPosition']
        item_num = mes_attr['extern_item_num']
        describe = mes_attr['extern_SubAttemperCode']
        item_version = mes_attr['extern_productversion']
        item_memo = mes_attr['extern_stritemmemo']
        workshop = mes_attr['extern_workshopname']
        daline = mes_attr['extern_biglinename']
        segment1 = '8'
        segemnt2 = ''
        segment3 = appconfig['wn'] + appconfig['wn_name'] + '[AutoTest]'
        sql = "insert into dmsnew.todayworkjob(workjob_code,item_code,item_type,line_code,testposition,item_num, " \
              "describe,item_version,item_memo,WORKSHOP,DALINE_CODE,SEGMENT1,SEGMENT2,SEGMENT3) " \
              "values('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}', '{7}', '{8}', '{9}', '{10}', '{11}', '{12}', '{13}')".format(
            workjob_code, item_code, item_type, line_code, testposition, item_num, describe, item_version, item_memo,
            workshop, daline, segment1, segemnt2, segment3)

        appconfig['mes_cursor'].execute(sql)
        appconfig['mes_conn'].commit()
    except Exception as e:
        appconfig['mes_conn'].rollback()
        appconfig['logger'].error(errorencode(traceback.format_exc()))

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class Logger(object):
    def __init__(self, name, file, level):
        self.__createLogger(name, file, level)

    def __createLogger(self, loggername, file, loggerlevel):
        self.logger = logging.getLogger(loggername)
        self.logger.setLevel(loggerlevel)
        self.logger.addHandler(self.__createHandler(file))

    def __createHandler(self, file):
        try:
            handler = logging.FileHandler(file)
        except TypeError as e :
            handler = logging.StreamHandler(file)
        handler.setFormatter(self.__createFormatter())
        return handler

    def __createFormatter(self):
        fmt = "%(asctime)s ip:{} level:%(levelname)s file:%(filename)s func:%(funcName)s line:%(lineno)d msg:%(message)s".format(socket.gethostbyname(socket.gethostname()))
        datefmt = "%Y-%m-%d %H:%M:%S"
        formatter = logging.Formatter(fmt, datefmt)
        return formatter

class ListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin):
    def __init__(self, parent, ID=-1, pos=wx.DefaultPosition, size=wx.DefaultSize, style=0):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)

#popupwindow to show listctrl(report mode) content
class PopupFrame(wx.Frame):
    def __init__(self, parent, id, title, pos , content, iconpath=None,style=wx.DEFAULT_FRAME_STYLE, size=wx.DefaultSize):
        wx.Frame.__init__(self, parent, id , title, pos, style=style, size=size)
        self.SetIcon(wx.Icon(iconpath))
        panel = wx.Panel(self)
        tc = wx.TextCtrl(panel, -1, style=wx.TE_MULTILINE | wx.TE_RICH2|wx.TE_NOHIDESEL)
        tc.SetValue( ftfy.fix_text( unicode(content) ))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(tc, 1, wx.EXPAND)
        panel.SetSizer(sizer)

class WiFiFrame(wx.Frame):
    def __init__(self, parent, id, title, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE, iconpath=None):
        wx.Frame.__init__(self, parent, id, title, pos, size, style)
        self.SetIcon(wx.Icon(iconpath))
        self.panel = wx.Panel(self)
        remove_wifi_profile_bn = wx.Button(self.panel, -1, u'清除所有无线网卡配置文件')
        create_wifi_bn = wx.Button(self.panel, -1, u'创建无线网络')

        self.Bind(wx.EVT_BUTTON, self.OnRemoveProfile, remove_wifi_profile_bn)
        self.Bind(wx.EVT_BUTTON, self.OnCreateWiFi, create_wifi_bn)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(remove_wifi_profile_bn, 1, wx.EXPAND)
        sizer.Add(create_wifi_bn, 1, wx.EXPAND)
        self.panel.SetSizer(sizer)
        self.statusbar = self.CreateStatusBar()

    def OnCreateWiFi(self, evt):
        self.statusbar.SetStatusText(u'该功能未实现')

    def OnRemoveProfile(self, evt):
        try:
            for iface in pywifi.PyWiFi().interfaces():
                iface.remove_all_network_profiles()
        except Exception as e:
            self.statusbar.SetStatusText(u'无线网卡配置文件清除失败')
        else:
            self.statusbar.SetStatusText(u'无线网卡配置文件清除成功')

class PDFPanel(wx.Panel):
    def __init__(self, parent=None):
        wx.Panel.__init__(self, parent=parent)
        self.buttonpanel = pdfButtonPanel(self, wx.NewId(), wx.DefaultPosition, wx.DefaultSize, 0)
        self.viewer = pdfViewer(self, wx.NewId(), wx.DefaultPosition, wx.DefaultSize, wx.HSCROLL | wx.VSCROLL | wx.SUNKEN_BORDER)
        self.buttonpanel.viewer = self.viewer
        self.viewer.buttonpanel = self.buttonpanel

        load_button = wx.Button(self, label=u'打开文件')
        load_button.Bind(wx.EVT_BUTTON, self.OnLoadButton)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(load_button, 0, wx.EXPAND)
        sizer.Add(self.buttonpanel, 0, wx.EXPAND)
        sizer.Add(self.viewer, 1, wx.EXPAND)
        self.SetSizerAndFit(sizer)

    def OnLoadButton(self, event):
        dlg = wx.FileDialog(self, wildcard="*.pdf")
        if dlg.ShowModal() == wx.ID_OK:
            wx.BeginBusyCursor()
            self.viewer.LoadFile(dlg.GetPath())
            wx.EndBusyCursor()
        dlg.Destroy()

class HTMLPanel(wx.Panel):
    def __init__(self, parent=None):
        wx.Panel.__init__(self, parent=parent)
        self.first_load = True
        self.url = ''
        self.refresh = wx.Button(self, label=u'刷新')
        self.webview = WebView.New(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.refresh, 0, wx.EXPAND)
        sizer.Add(self.webview, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.refresh.Bind(wx.EVT_BUTTON, self.OnRefresh)

    def FirstLoad(self, url):
        self.url = url
        if self.first_load:
            self.webview.LoadURL(self.url)
            self.first_load = False

    def OnRefresh(self, evt):
        self.webview.Reload()

class PanelText(wx.Panel):
    def __init__(self, parent=None):
        wx.Panel.__init__(self, parent=parent)
        self.first_load = True
        self.content = ''
        self.refresh = wx.Button(self, label=u'刷新')
        self.text = wx.TextCtrl(self, style=wx.TE_MULTILINE|wx.TE_READONLY)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.refresh, 0, wx.EXPAND)
        sizer.Add(self.text, 1, wx.EXPAND)
        self.SetSizer(sizer)
        self.refresh.Bind(wx.EVT_BUTTON, self.OnRefresh)

    def FirstLoad(self, content):
        self.content = content
        if self.first_load:
            self.text.Clear()
            self.text.AppendText(self.content)
            self.text.SetInsertionPoint(0)
            self.first_load = False

    def OnRefresh(self, evt):
        self.first_load = True
        self.FirstLoad(self.content)


class BugFrame( wx.Frame):
    def __init__(self, parent, title='', size=wx.DefaultSize, appconfig={}):
        wx.Frame.__init__(self, parent=parent, title=title, size=size, name='BugFrame')
        self.appconfig = appconfig
        self.SetIcon(wx.Icon(self.appconfig['iconpath']))
        self.book = wx.Notebook(self, -1, style=wx.NB_MULTILINE)

        self.book.InsertPage(0, PanelText(self.book), '程序异常信息')
        self.book.InsertPage(1, PanelText(self.book), '脚本运行信息')
        self.book.InsertPage(2, VariablePanel(self.book), '脚本运行变量')
        self.book.InsertPage(3, RePanel(self.book), '表达式验证')
        self.book.InsertPage(4, PanelText(self.book), '更新说明')
        self.book.InsertPage(5, HTMLPanel(self.book), '脚本配置说明')
        self.book.InsertPage(6, FTPServerPanel(self.book), 'FTP Server')
        self.book.InsertPage(7, TFTPServerPanel(self.book), 'TFTP Server')
        self.book.InsertPage(8, SearchPanel(self.book, appconfig), '数据库查询')
        self.book.InsertPage(9, PDFPanel(self.book), 'PDF阅读器')
        self.book.InsertPage(10, shell.Shell(self.book), 'Shell')
        self.book.InsertPage(11, HTMLPanel(self.book), '平台使用说明书')

        self.book.Bind(wx.EVT_BOOKCTRL_PAGE_CHANGED, self.OnChanged)
        self.book.Bind(wx.EVT_BOOKCTRL_PAGE_CHANGING, self.OnChanging)
        self.book.SetPadding((5, 0))
        self.book.SetSelection(0)

        self.Bind(wx.EVT_CLOSE, self.OnClose)

    def OnClose(self, evt):
        page = self.book.GetPage(7)
        page.StopTFTPServer(None)

        page = self.book.GetPage(6)
        page.StopFTPServer(None)
        self.Destroy()

    def OnChanging(self, evt):
        pub.sendMessage('TOPIC_APPCONFIG_RECEIVE')

    def OnChanged(self, evt):
        pageNumber = evt.GetSelection()
        if pageNumber == 0:
            page = self.book.GetPage(pageNumber)
            page.FirstLoad(self.appconfig['debug_handle'].getvalue())
        elif pageNumber == 1:
            page = self.book.GetPage(pageNumber)
            page.FirstLoad(self.appconfig['process_handle'].getvalue())
        elif pageNumber == 2:
            page = self.book.GetPage(pageNumber)
            page.FirstLoad(self.appconfig['var_im'])
        elif pageNumber == 3:
            page = self.book.GetPage(pageNumber)
            page.appconfig = self.appconfig
        elif pageNumber == 4:
            page = self.book.GetPage(pageNumber)
            update_log = os.path.join(self.appconfig['doc_dir'], 'update_log.txt')
            content = io.open(update_log, encoding='utf-8').read()
            page.FirstLoad(content)
        elif pageNumber == 5:
            page = self.book.GetPage(pageNumber)
            page.FirstLoad('ftp://192.168.60.70/AutoTest-Config/example/example.xml')
        elif pageNumber == 6:
            page = self.book.GetPage(pageNumber)
            page.RefreshChoice()
        elif pageNumber == 7:
            page = self.book.GetPage(pageNumber)
            page.RefreshChoice()
        elif pageNumber == 11:
            page = self.book.GetPage(pageNumber)
            soft_instruction_path = os.path.join(self.appconfig['doc_dir'], 'soft_ins.html')
            page.FirstLoad(soft_instruction_path)

class SearchPanel(wx.Panel, listmix.ColumnSorterMixin):
    def __init__(self, parent=None, appconfig={}):
        wx.Panel.__init__(self, parent=parent)
        self.panel = self
        self.log_cursor = appconfig['log_cursor']
        self.iconpath = appconfig['iconpath']
        sz = (-1, 25)
        self.workorder_st = wx.StaticText(self.panel, -1, u'工单号:', style=wx.ALIGN_BOTTOM, size=sz)
        self.workorder_tc = wx.TextCtrl(self.panel, -1, '', size=sz)

        self.sn_st = wx.StaticText(self.panel, -1, 'SN:', style=wx.ALIGN_BOTTOM, size=sz)
        self.sn_tc = wx.TextCtrl(self.panel, -1, '', size=(210, -1))

        time_st = wx.StaticText(self.panel, -1, '时间:', style=wx.ALIGN_LEFT, size=sz)
        self.starttime_picker = wx.adv.DatePickerCtrl(self.panel)
        dash_st = wx.StaticText(self.panel, -1, '-', style=wx.ALIGN_BOTTOM, size=sz)
        self.endtime_picker = wx.adv.DatePickerCtrl(self.panel)
        sizer_time = wx.BoxSizer(wx.HORIZONTAL)
        sizer_time.Add(time_st)
        sizer_time.Add(self.starttime_picker, 0, wx.LEFT, 5)
        sizer_time.Add(dash_st, 0, wx.LEFT, 5)
        sizer_time.Add(self.endtime_picker, 0, wx.LEFT, 5)

        operator_st = wx.StaticText(self.panel, -1, '操作员:', style=wx.ALIGN_BOTTOM, size=sz)
        self.operator_tc = wx.TextCtrl(self.panel, -1, '')

        productname_st = wx.StaticText(self.panel, -1, '产品名称:', style=wx.ALIGN_BOTTOM, size=sz)
        self.productname_tc = wx.TextCtrl(self.panel, -1, '')

        result_st = wx.StaticText(self.panel, -1, '结果:', style=wx.ALIGN_BOTTOM, size=sz)
        self.result_choice = wx.Choice(self.panel, choices=['', 'PASS', 'FAIL'])

        self.export_bn = wx.Button(self.panel, -1, u'导出', size=sz)
        self.search_bn = wx.Button(self.panel, -1, 'Search', size=sz)
        self.export_bn.Bind(wx.EVT_BUTTON, self.OnExportData)

        suite_in, suite_out = 5, 10
        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        hsizer.Add(self.workorder_st, 0, wx.EXPAND | wx.RIGHT, suite_in)
        hsizer.Add(self.workorder_tc, 0, wx.EXPAND | wx.RIGHT, suite_out)
        hsizer.Add(self.sn_st, 0, wx.EXPAND | wx.RIGHT, suite_in)
        hsizer.Add(self.sn_tc, 0, wx.EXPAND | wx.RIGHT, suite_out)

        hsizer.Add(sizer_time, 0, wx.EXPAND | wx.RIGHT, suite_out)
        hsizer.Add(operator_st, 0, wx.EXPAND | wx.RIGHT, suite_in)
        hsizer.Add(self.operator_tc, 0, wx.EXPAND | wx.RIGHT, suite_out)
        hsizer.Add(productname_st, 0, wx.EXPAND | wx.RIGHT, suite_in)
        hsizer.Add(self.productname_tc, 0, wx.EXPAND | wx.RIGHT, suite_out)
        hsizer.Add(result_st, 0, wx.EXPAND | wx.RIGHT, suite_in)
        hsizer.Add(self.result_choice, 0, wx.EXPAND | wx.RIGHT, suite_out)

        hsizer.AddStretchSpacer()
        hsizer.Add(self.export_bn, 0, wx.RIGHT|wx.EXPAND, 5)
        hsizer.Add(self.search_bn, 0, wx.EXPAND)

        self.list_lc = ListCtrl(self.panel, -1, style=wx.LC_REPORT | wx.BORDER_NONE | wx.LC_SORT_ASCENDING)
        columns = [u'IDX', u'ID', u'工序' , u'线体' , u'SN', u'MAC', u'结果', u'起始时间', u'结束时间', u'测试时间', u'操作员', u'工单号', u'BOM编码', u'产品名称', u'产品版本', u'批次号',
                   u'串口日志', u'测试项日志', u'物料代码', u'备注']
        for col, text in enumerate(columns):
            self.list_lc.InsertColumn(col, text)
        listmix.ColumnSorterMixin.__init__(self, self.list_lc.GetColumnCount())
        vsizer = wx.BoxSizer(wx.VERTICAL)
        vsizer.Add(hsizer, 0, wx.EXPAND | wx.BOTTOM)
        vsizer.Add(self.list_lc, 1, wx.EXPAND)
        self.panel.SetSizer(vsizer)
        self.list_lc.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        self.Bind(wx.EVT_BUTTON, self.OnSearch, self.search_bn)

    def OnExportData(self, evt):
        start_datetime = self.starttime_picker.GetValue()
        end_datetime = self.endtime_picker.GetValue()
        if self.productname_tc.GetValue():
            defaultFileName = '{} {}-{}'.format(self.productname_tc.GetValue(), start_datetime.Format("%Y%m%d"), end_datetime.Format("%Y%m%d"))
        else:
            defaultFileName = '{}-{}'.format(start_datetime.Format("%Y%m%d"), end_datetime.Format("%Y%m%d"))
        dlg = wx.FileDialog(self, message="保存", defaultDir='',defaultFile=defaultFileName,
                            wildcard=u"Excel97 文件 (*.xls)|*.xls|Excel2010 文件 (*.xlsx)|*.xlsx|csv 文件 (*.csv)|*.csv", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT|wx.FD_CHANGE_DIR)
        df = pd.DataFrame(self.itemDataMap)
        df = df.transpose()
        df = df.fillna(value='')
        if dlg.ShowModal() ==  wx.ID_OK:
            columns = []
            for col_id in self.list_lc.GetColumnsOrder():
                colobj = self.list_lc.GetColumn(col_id)
                columns.append(colobj.GetText())
            df.columns = columns
            df = df.drop(columns=[u'IDX', u'ID', u'串口日志', u'测试项日志'])
            if os.path.splitext(dlg.GetFilename())[1] == '.csv':
                df.to_csv(dlg.GetPath(), encoding='gbk')
            else:
                df.to_excel(dlg.GetPath(), sheet_name=defaultFileName)

    def OnSearch(self, evt):
        # sql = "select sn, segment1 ,result, starttime, endtime, totaltime, operator, workorder, bomcode, productname, productver, lotno, logserial, logprocess, segment2 ,description from sn_table"
        # sql = "select id, sn, segment1 ,result, starttime, endtime, totaltime, operator, workorder, bomcode, productname, productver, lotno, segment2 ,description from sn_table"
        sql = "select @rownr:=@rownr+1 as idx, id, segment3, segment4, sn, segment1 ,result, starttime, endtime, totaltime, operator, workorder, bomcode, productname, productver, lotno, '', '' ,segment2 ,description from sn_table"
        sn = self.sn_tc.GetValue().strip()
        order = self.workorder_tc.GetValue().strip()
        starttime = self.starttime_picker.GetValue().FormatISODate()
        endtime = self.endtime_picker.GetValue().FormatISODate()
        operator = self.operator_tc.GetValue().strip()
        productname = self.productname_tc.GetValue().strip()
        result = self.result_choice.GetString(self.result_choice.GetSelection())

        sql += " where sn like \"%{}%\" and ifnull(workorder, '') like \"%{}%\" and operator like \"%{}%\" " \
               "and productname like \"%{}%\"  and result like \"%{}%\"  and starttime >= \"{}\" and endtime <= date_add(\"{}\", interval 1 day) ".format(
            sn, order, operator, productname, result, starttime, endtime)
        self.list_lc.DeleteAllItems()
        self.log_cursor.execute("set @rownr=0")
        self.log_cursor.execute(sql)
        sql_value = self.log_cursor.fetchall()
        self.itemDataMap = {}

        for row, rowdata in enumerate(sql_value):
            self.itemDataMap[row] = rowdata

        for key, rowdata in self.itemDataMap.items():
            index = self.list_lc.InsertItem(sys.maxint, str(key))
            self.list_lc.SetItemData(index, key)
            for col in range(self.list_lc.GetColumnCount()):
                self.list_lc.SetItem(index, col, mes_value(rowdata[col]))

    def OnLeftDClick(self, evt):
        item, where, subitem = self.list_lc.HitTestSubItem(evt.GetPosition())
        data = self.itemDataMap[self.list_lc.GetItemData(item)]
        pos = self.list_lc.ClientToScreen(evt.GetPosition())
        col_info = self.list_lc.GetColumn(subitem)
        title = data[4] + ' -- ' + col_info.GetText()

        if col_info.GetText() == '串口日志':
            sql = "select logserial from sn_table where id={}".format(data[1])
            self.log_cursor.execute(sql)
            sql_value = self.log_cursor.fetchone()
            pop_content = sql_value[0]
        elif col_info.GetText() == '测试项日志':
            sql = "select logprocess from sn_table where id={}".format(data[1])
            self.log_cursor.execute(sql)
            sql_value = self.log_cursor.fetchone()
            pop_content = sql_value[0]
        else:
            pop_content = data[subitem]
        popup_win = PopupFrame(self, -1, title, pos, pop_content, self.iconpath, size=(500, -1))
        popup_win.Show()

    def GetListCtrl(self):
        return self.list_lc


class DownLoadWindow(wx.Frame):
    def __init__(self, parent, title, size=wx.DefaultSize, appconfig={}):
        self.mes_cursor = appconfig['mes_cursor']
        extern_WJTableName = appconfig['mes_attr']['extern_WJTableName']
        extern_StationName = appconfig['mes_attr']['extern_StationName']
        wx.Frame.__init__(self, parent = parent, title = title, size=size)
        self.panel = wx.Panel(self, style=wx.WANTS_CHARS)
        self.infobar = wx.InfoBar(self.panel)
        sql_field = ','.join(["workjob_code", "code", "testposition"   , "softcode" , "softname", "softtype", "softver"  ,"filename" , "filepath",
                              "item_describe", "item_version", "item_type", "item_code" ])
        columns = [u'任务单号',  u'单据号', u'工序', u'软件编码', u'软件名称', u'软件类型', u'软件版本',  u'文件名称', u'文件路径', u'产品名称', u'产品版本', u'产品类型', u'产品编码']
        sql = "select {}  from DMSNEW.tab_productsubsoftware_history w where w.WORKJOB_CODE='{}' and w.realtestposition ='{}' and  w.createdate = (SELECT MAX(CREATEDATE) FROM \
                    DMSNEW.tab_productsubsoftware_history w where w.WORKJOB_CODE='{}' and w.realtestposition ='{}')".format(sql_field, extern_WJTableName, extern_StationName,extern_WJTableName, extern_StationName)

        self.data  = self.mes_cursor.execute(sql).fetchall()
        self.list = ListCtrl(self.panel, -1, style=wx.LC_REPORT)

        for col, label in enumerate(columns):
            self.list.InsertColumn(col, label)

        for row, value in enumerate(self.data):
            self.list.InsertItem(row, '')
            for col in range(len(columns)):
                if value[col] != None:
                    self.list.SetItem(row, col, unicode(value[col]))
                else:
                    self.list.SetItem(row, col, '')

        for col in range(len(columns)):
            self.list.SetColumnWidth(col, wx.LIST_AUTOSIZE)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.infobar, wx.SizerFlags().Expand())
        sizer.Add(self.list, 1, wx.GROW)
        self.panel.SetSizer(sizer)
        self.list.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        # self.statusbar = self.CreateStatusBar(style=wx.STB_SIZEGRIP)

    def OnRightDown(self, evt):
        menu = wx.Menu()
        downloaditem = menu.Append(-1, u'下载')
        self.Bind(wx.EVT_MENU, self.OnDownLoadFile, downloaditem)
        self.PopupMenu(menu)

    def OnDownLoadFile(self, evt):
        sel_data = self.data[self.list.GetFocusedItem()]
        sql = " SELECT  ftpaddress,ftpport,ftpuser,ftppass,ftppath,segment2 from DMSNEW.TAB_FTPSENDLOADINFOR where ftptype ='SOFT' and segment1 ='下载'  "
        sql_value = self.mes_cursor.execute(sql).fetchone()
        ftpaddress = mes_value(sql_value[0] )
        ftpport = mes_value(sql_value[1])
        ftpuser = mes_value(sql_value[2])
        ftppass = mes_value(sql_value[3])
        ftppath = mes_value(sql_value[4])

        ftp = ftputil.FTPHost(ftpaddress, ftpuser, ftppass)
        # basedir  = '/{}'.format(ftppath) if sel_data[8] == None  else sel_data[8]
        basedir = '/{}/{}'.format(ftppath, sel_data[8])
        filename = sel_data[7]
        filepath = os.path.normpath( os.path.join(basedir, filename) )

        dlg = wx.FileDialog(self, message="Save file as ...", defaultDir=wx.GetUserName(), defaultFile=filename,
                            style=wx.FD_SAVE | wx.FD_CHANGE_DIR | wx.FD_OVERWRITE_PROMPT)
        dlg.SetWildcard("All files (*.*)|*.*|" + "Text file (*.txt)|*.txt|" + "Binary file (*.bin)|*.bin|")

        if dlg.ShowModal() == wx.ID_OK:
            remote_filepath = filepath.decode('utf-8').encode('gbk')
            try:
                ftp.download(remote_filepath, dlg.GetPath())
            except ftputil.error.FTPIOError as e:
                self.infobar.ShowMessage(u'文件不存在, 软件下载失败', flags=wx.ICON_ERROR)
            else:
                self.infobar.ShowMessage(u'软件下载成功')
            finally:
                ftp.close()

class DownLoadSopWindow(wx.Frame):
    def __init__(self, parent, title, size=wx.DefaultSize, appconfig={}):
        self.mes_cursor = appconfig['mes_cursor']
        extern_SubAttemperCode = appconfig['mes_attr']['extern_SubAttemperCode']
        extern_stritemcode = appconfig['mes_attr']['extern_stritemcode']
        extern_StationName = appconfig['mes_attr']['extern_StationName']
        wx.Frame.__init__(self, parent = parent, title = title, size=size)

        self.panel = wx.Panel(self, style=wx.WANTS_CHARS)
        self.infobar = wx.InfoBar(self.panel)
        sql_field = ','.join(['CODE','ID','TESTPOSITIONNAME','TESTPOSITIONCODE','FLAG','FILENAME','FILEITEMTYPE',
                              'FILEPATH','FILEDESCRIBE','DESCRIBE','inputman','INPUTDATE','ITEMCODE','ITEMTYPE','ITEMVERSION','ITEMDESCRIBE','ITEMLINE'])
        columns = [u'单据号',  u'序号', u'工序', u'工序代码', u'SOP编码', u'文件名称', u'版本类型',  u'文件路径', u'文件说明', u'备注', u'修改人', u'录入日期',
                   u'产品编码', u'产品型号', u'产品版本', u'产品名称', u'产品系列']

        sql = "select m.mpkbeginbarcode  from DMSNEW.mtl_sub_attemper  m where m.sub_attempter_code ='{}' ".format(extern_SubAttemperCode)
        sql_value = self.mes_cursor.execute(sql).fetchone()
        if sql_value[0] is None:
            sql = "select {} from DMSNEW.view_TAB_SOPSUBBOOK where ITEMCODE='{}'  and TESTPOSITIONNAME='{}' order by code,id ".format(sql_field, extern_stritemcode, extern_StationName)
        else:
            sql = "select {} from DMSNEW.view_TAB_SOPSUBBOOK where ITEMCODE='{}' and flag in " \
                  "(select column_value from table(f_split('{}',',')) where column_value is not null ) " \
                  "order by code,id ".format(sql_field, extern_stritemcode, sql_value[0])

        self.data  = self.mes_cursor.execute(sql).fetchall()
        self.list = ListCtrl(self.panel, -1, style=wx.LC_REPORT)

        for col, label in enumerate(columns):
            self.list.InsertColumn(col, label)

        for row, value in enumerate(self.data):
            self.list.InsertItem(row, '')
            for col in range(len(columns)):
                if value[col] != None:
                    self.list.SetItem(row, col, unicode(value[col]))
                else:
                    self.list.SetItem(row, col, '')

        for col in range(len(columns)):
            self.list.SetColumnWidth(col, wx.LIST_AUTOSIZE)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.infobar, wx.SizerFlags().Expand())
        sizer.Add(self.list, 1, wx.GROW)
        self.panel.SetSizer(sizer)
        self.list.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
        # self.statusbar = self.CreateStatusBar(style=wx.STB_SIZEGRIP)

    def OnRightDown(self, evt):
        menu = wx.Menu()
        downloaditem = menu.Append(-1, u'下载')
        self.Bind(wx.EVT_MENU, self.OnDownLoadFile, downloaditem)
        self.PopupMenu(menu)

    def OnDownLoadFile(self, evt):
        sel_data = self.data[self.list.GetFocusedItem()]
        sql = " SELECT  ftpaddress,ftpport,ftpuser,ftppass,ftppath,segment2 from dmsnew.TAB_FTPSENDLOADINFOR where ftptype ='SOP' and segment1 ='下载'  "
        sql_value = self.mes_cursor.execute(sql).fetchone()
        ftpaddress = mes_value(sql_value[0] )
        ftpport = mes_value(sql_value[1])
        ftpuser = mes_value(sql_value[2])
        ftppass = mes_value(sql_value[3])
        ftppath = mes_value(sql_value[4])
        ftppathshare = mes_value(sql_value[5])

        filename, filepath = sel_data[5], sel_data[7]
        if filename == '':
            self.infobar.ShowMessage(u'SOP名称为空，不能查阅作业指导书')
            return

        if filepath == '':
            self.infobar.ShowMessage(u'SOP文件路径为空，不能查阅作业指导书')
            return

        ftp = ftputil.FTPHost(ftpaddress, ftpuser, ftppass)
        if filepath != '':
            soppath = os.path.join('\\',ftppathshare, filepath, filename)
        else:
            soppath = os.path.join('\\',ftppathshare, filename)

        soppath = os.path.normpath(soppath)
        dlg = wx.FileDialog(self, message="Save file as ...", defaultDir=wx.GetUserName(), defaultFile=filename,
                            style=wx.FD_SAVE | wx.FD_CHANGE_DIR | wx.FD_OVERWRITE_PROMPT)
        dlg.SetWildcard("All files (*.*)|*.*|" + "Text file (*.txt)|*.txt|" + "Binary file (*.bin)|*.bin|")

        if dlg.ShowModal() == wx.ID_OK:
            try:
                ftp.download(soppath.encode('gb2312'), dlg.GetPath())
            except ftputil.error.FTPIOError as e:
                self.infobar.ShowMessage(u'{} 下载失败'.format(filename), flags=wx.ICON_ERROR)
            else:
                self.infobar.ShowMessage(u'{} 下载成功'.format(filename))
            finally:
                ftp.close()

class AvailablePort(object):
    FLAG = False
    PORTS = []
    ALL_PORTS = []
    __root = None
    @classmethod
    def get(cls, appconfig={}, all=False):
        if cls.__root is None:
            parser = etree.XMLParser(encoding='utf-8', remove_blank_text=True, remove_comments=True)
            cls.__root = etree.parse(appconfig['setting_file'], parser).getroot()

        if cls.FLAG == True:
            return cls.ALL_PORTS if all else cls.PORTS
        for port in serial_comports():
            try:
                serial.Serial(port[0]).close()
            except Exception as e:
                pass
            else:
                node = cls.__root.find(".//port[@name='{}']".format(port[0]))
                cls.ALL_PORTS.append(port[0])
                if node.get('enable') == "True": cls.PORTS.append(port[0])

        cls.FLAG = True
        try:
            cls.PORTS = sorted(cls.PORTS, key=lambda k:int(k[3:]) )
            cls.ALL_PORTS = sorted(cls.ALL_PORTS, key=lambda k:int(k[3:]) )
        except Exception as e:
            cls.PORTS = sorted(cls.PORTS)
            cls.ALL_PORTS = sorted(cls.ALL_PORTS, key=lambda k: int(k[3:]))

        return cls.ALL_PORTS if all else cls.PORTS


class Validator(wx.Validator):
    def __init__(self, type):
        wx.Validator.__init__(self)
        self.type = type

    def Clone(self):
        return Validator(self.type)

    def Validate(self, parent):
        win = self.GetWindow()
        value = win.GetValue()
        if self.type == 'ip':
            valid_ip_re = "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$";
            if re.match(valid_ip_re, value):
                return True
        elif self.type == 'number':
            if value.isdigit():
                return True

        win.SetBackgroundColour('pink')
        win.SetFocus()
        win.Refresh()
        return False

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True


class TelnetSettingDialog(wx.Dialog):
    def __init__(self, data, titile=u'Telent端口设置'):
        wx.Dialog.__init__(self, parent=None, title=titile)
        # (serial.Serial attribute, label text, choice selection list)
        self.data = data
        self.SetTitle('{}'.format(self.data['name']))
        self.setting_file = self.data['setting_file']

        ip, port = tuple(self.data['name'].split(':'))
        self.ip_label = wx.StaticText(self, label='IP地址：')
        self.ip_input = wx.TextCtrl(self, -1, value= ip, validator=Validator(type='ip'))

        self.port_label = wx.StaticText(self, label='端口：')
        self.port_input = wx.TextCtrl(self, -1, value= port, size=(50, -1), validator=Validator(type='number'))

        host_sizer = wx.BoxSizer(wx.HORIZONTAL)
        host_sizer.Add(self.ip_label, 0, wx.LEFT | wx.EXPAND, 5)
        host_sizer.Add(self.ip_input, 0, wx.RIGHT| wx.EXPAND, 5)
        host_sizer.Add(self.port_label, 0, wx.RIGHT|wx.EXPAND)
        host_sizer.Add(self.port_input, 0, wx.EXPAND)

        # ok, cancel button
        okay = wx.Button(self, wx.ID_OK)
        okay.SetDefault()
        cancel = wx.Button(self, wx.ID_CANCEL)
        btsz = wx.StdDialogButtonSizer()
        btsz.AddButton(okay)
        btsz.AddButton(cancel)
        btsz.Realize()

        # place two sizer in vertical style
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(host_sizer, 0, wx.GROW)
        sizer.Add(btsz, 0, wx.GROW|wx.TOP, 5)
        self.SetSizerAndFit(sizer)

    def SaveChange(self):pass

    def GetValue(self):
        value_dict = {}
        value_dict['ip'] = self.ip_input.GetValue().strip()
        value_dict['port'] = self.port_input.GetValue().strip()
        value_dict['name'] = '{}:{}'.format(value_dict['ip'], value_dict['port'])
        return value_dict

#端口设置
class SerialSettingDialog(wx.Dialog):
    def __init__(self, data, titile=u'串口设置'):
        wx.Dialog.__init__(self, parent=None, title=titile)
        #(serial.Serial attribute, label text, choice selection list)
        wsz = [100, -1]
        self.data = data
        self.setting_file, self.com = self.data['setting_file'], self.data['name']
        self.SetTitle('{}串口设置'.format(self.com))

        parser = etree.XMLParser(encoding='utf-8', remove_blank_text=True, remove_comments=True)
        self.tree = etree.parse(self.setting_file, parser)
        self.root = self.tree.getroot()
        self.node = self.root.find(".//port[@name='{}']".format(self.com))

        port_pair = ('name', '端口：', AvailablePort.get(), 0)
        stopbit_pair = ('stopbits', '停止位：', ['1', '2'],  0)
        databit_pair = ('bytesize', '数据位：', ['5', '6', '7', '8'],  3)
        flow_pair = ('timeout', '读超时：', ['0' , '1', '2', '3', '4'],  1)
        parity_pair = ('parity', '校验位：', ['N', 'E', 'O', 'S', 'M'],  0)
        baudrate_pair = ('baudrate', '波特率：', ['9600', '115200'], 0)
        option_sizer = wx.FlexGridSizer(cols=6, hgap=6, vgap=6)

        for name, text, choices, default_sel in [port_pair, stopbit_pair, databit_pair, flow_pair, parity_pair, baudrate_pair]:
            label = wx.StaticText(self, label=unicode(text))
            choice = wx.Choice(self, choices=choices, size=wsz, name=name)
            choice.Bind(wx.EVT_CHOICE, self.OnChoice)
            choice.SetSelection(choices.index(self.node.get(name)) )
            if name == "name": choice.Enable(False)
            option_sizer.Add(label, 0, wx.ALL | wx.ALIGN_CENTER)
            option_sizer.Add(choice, 0, wx.ALL | wx.ALIGN_CENTER)

        #ok, cancel button
        okay = wx.Button(self, wx.ID_OK)
        okay.SetDefault()
        cancel = wx.Button(self, wx.ID_CANCEL)
        btsz = wx.StdDialogButtonSizer()
        btsz.AddButton(okay)
        btsz.AddButton(cancel)
        btsz.Realize()

        #place two sizer in vertical style
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(option_sizer, 0, wx.GROW)
        sizer.Add(btsz, 0, wx.GROW)
        self.SetSizerAndFit(sizer)

    def OnChoice(self, evt):
        obj = evt.GetEventObject()
        attr_name, attr_value = obj.GetName(), evt.GetString()
        self.node.set(attr_name, attr_value)

    def SaveChange(self):
        self.tree.write(self.setting_file, encoding='utf-8', pretty_print=True, xml_declaration=True)

    def GetValue(self):
        return ParseSeqXML.get_element_dict(self.node)

def settingdialog_factory(data, type):
    if type == 'telnet':
        return TelnetSettingDialog(data)
    elif type == 'serial':
        return SerialSettingDialog(data)

#section window show test unit's process message
class SectionWindow(wx.lib.scrolledpanel.ScrolledPanel):
    def __init__(self, parent):
        wx.lib.scrolledpanel.ScrolledPanel.__init__(self, parent=parent)
        self.section_log = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH)
        #let section log stretch over then window
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.section_log, 1, wx.GROW)
        self.SetSizerAndFit(sizer)
    #append message to section log
    def AppendMessage(self, data):
        self.section_log.AppendText(data)

#message window show runtime message of log area and section
class MessageWindow(wx.SplitterWindow):
    def __init__(self, parent):
        wx.SplitterWindow.__init__(self, parent=parent)
        self.parent = parent
        #when a period end, show process info
        self.section_window = SectionWindow(self)
        #when enter command, append serial message to log area
        self.log_area = wx.TextCtrl(self, -1, style=wx.TE_MULTILINE |wx.TE_READONLY| wx.TE_RICH|wx.TE_PROCESS_TAB|wx.TE_PROCESS_ENTER)
        self.log_area.Bind(wx.EVT_CHAR, self.OnChar)
        self.log_area.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
        self.log_area.Bind(wx.EVT_KEY_UP, self.OnkeyUp)
        self.log_area.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        #split it and set minium size
        self.SplitHorizontally(self.section_window, self.log_area)
        self.SetMinimumPaneSize(50)
        self.SetSashPosition(150)

        self.prev_char = None
        self.normal_char_storage = []
        self.special_char_storage = []

    def OnCharHook(self, evt):
        keycode, keychar = evt.GetKeyCode(), unichr(evt.GetKeyCode())
        if keycode == wx.WXK_TAB:
            self.parent.dev.write(bytes(keychar))
        else:
            evt.DoAllowNextEvent()

    def OnkeyUp(self, evt):
        self.prev_char = None
        evt.Skip()

    def OnKeyDown(self, evt):
        keycode, keychar = evt.GetKeyCode(), unichr(evt.GetKeyCode())
        if self.prev_char == wx.WXK_CONTROL and keychar == '6' and self.parent.dev.alive():
            self.parent.dev.write(binascii.unhexlify("1e"))
        if evt.GetKeyCode() == wx.WXK_CONTROL:
            self.prev_char = wx.WXK_CONTROL
        evt.Skip()

    def OnChar(self, evt):
        if self.parent.dev.alive():
            self.parent.dev.write(bytes(unichr(evt.GetKeyCode())))
        evt.Skip()

    def AppendContent(self, text):
        self.log_area.AppendText(text)

class RePanel(wx.Panel):
    def __init__(self, parent=None):
        wx.Panel.__init__(self, parent=parent )
        self.appconfig = {}
        self.win = MultiSplitterWindow(self)
        # for tename, title, pos in (('whole_te', 'Whole Text', (0, 100)), ('part_te', 'Part Text', (0, 200)), ('re_te', 'Regular Expresion', (0, 250))):
        #     self.createTe(tename, title, pos)

        for tename, title, pos in (('whole_te', 'Whole Text', (0, 0)), ('re_te', 'Regular Expresion', (0, 200))):
            self.createTe(tename, title, pos)
        self.win.SetOrientation(wx.VERTICAL)

        self.info_bar = wx.InfoBar(self)
        file_button = wx.Button(self, label="Get File List")
        test_button = wx.Button(self, label='Execute')
        test_button.Bind(wx.EVT_BUTTON, self.OnReTest)
        file_button.Bind(wx.EVT_BUTTON, self.OnGetFile)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(file_button, 0, wx.EXPAND)
        sizer.Add(self.win, 1, wx.EXPAND)
        sizer.Add(test_button, 0, wx.EXPAND)
        sizer.Add(self.info_bar, 0, wx.EXPAND)
        self.SetSizer(sizer)

    def createTe(self, tename='', title='', pos=0):
        panel = wx.Panel(self.win)
        sizer = wx.StaticBoxSizer(wx.VERTICAL, panel, label=title)
        setattr(self, tename, wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_RICH2))
        sizer.Add(getattr(self, tename), 1, wx.EXPAND)
        panel.SetSizer(sizer)
        self.win.AppendWindow(panel)
        self.win.SetSashPosition(pos[0], pos[1])

    def OnGetFile(self, evt):
        extern_WJTableName = self.appconfig['mes_attr']['extern_WJTableName']
        extern_StationName = self.appconfig['mes_attr']['extern_StationName']
        sql = "select filename  from DMSNEW.tab_productsubsoftware_history w where w.WORKJOB_CODE='{}' and w.realtestposition ='{}' and  w.createdate = (SELECT MAX(CREATEDATE) FROM \
                                  DMSNEW.tab_productsubsoftware_history w where w.WORKJOB_CODE='{}' and w.realtestposition ='{}')".format(
            extern_WJTableName, extern_StationName, extern_WJTableName, extern_StationName)
        filenams_list = self.appconfig['mes_cursor'].execute(sql).fetchall()
        for file_item in filenams_list:
            self.whole_te.AppendText(file_item[0] + '\n')

    def OnReTest(self, evt):
        whole_text = self.whole_te.GetValue()
        # part_text = self.part_te.GetValue()
        part_text = whole_text

        style = wx.TextAttr("RED", "WHITE")
        base_pos = whole_text.find(part_text)
        self.whole_te.SetStyle(0, len(whole_text) - 1, wx.TextAttr("BLACK", "WHITE"))

        for lineNo in range(self.re_te.GetNumberOfLines()):
            match_re_line = self.re_te.GetLineText(lineNo)
            match = re.search(match_re_line.strip(), part_text)
            if match and len(match.groups()):
                try:
                    match_relative_pos = match.span(1)
                    match_absolute_pos = (match_relative_pos[0] + base_pos, match_relative_pos[1] + base_pos)
                    self.whole_te.SetStyle(match_absolute_pos[0], match_absolute_pos[1], style)
                    self.whole_te.SetInsertionPoint(match_absolute_pos[0])
                except Exception as e:
                    print traceback.format_exc()


class VariablePanel(wx.Panel, listmix.ColumnSorterMixin):
    def __init__(self, parent=None):
        wx.Panel.__init__(self, parent=parent)
        self.first_load = True
        self.dataDict = {}
        self.list = ListCtrl(self, style=wx.LC_REPORT | wx.LC_HRULES | wx.LC_VRULES)
        self.list.InsertColumn(1, u'名称', width=180)
        self.list.InsertColumn(2, u'值')
        listmix.ColumnSorterMixin.__init__(self, self.list.GetColumnCount())

        self.refresh = wx.Button(self, label=u'刷新')
        self.refresh.Bind(wx.EVT_BUTTON, self.OnRefresh)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.refresh, 0, wx.EXPAND)
        sizer.Add(self.list, 1, wx.EXPAND)
        self.SetSizer(sizer)

    def FirstLoad(self, dataDict={}):
        self.dataDict = dataDict
        if self.first_load:
            self.itemDataMap = {}
            self.list.DeleteAllItems()
            for idx, key in enumerate(self.dataDict):
                self.itemDataMap[idx] = (key, self.dataDict[key])
                item = self.list.InsertItem(sys.maxint, key)
                self.list.SetItem(item, 1, str(self.dataDict[key]))
                self.list.SetItemData(item, idx)
            self.first_load = False

    def OnRefresh(self, evt):
        self.first_load = True
        self.FirstLoad(self.dataDict)

    def GetListCtrl(self):
        return self.list


class MyHandler(FTPHandler):
    log_area = None
    def on_connect(self):
        if self.log_area:
            self.log_area.AppendText('----------{}----------\n'.format(self.banner))
            self.log_area.AppendText(u'<{}:{}> 连接\n'.format(self.remote_ip, self.remote_port))

    def on_disconnect(self):
        if self.log_area:
            self.log_area.AppendText(u'<{}:{}> {} 断开连接\n'.format(self.remote_ip, self.remote_port, self.username ))

    def on_login(self, username):
        if self.log_area:
            self.log_area.AppendText(u'<{}:{}> {} 登陆\n'.format(self.remote_ip, self.remote_port, self.username))

    def on_logout(self, username):
        if self.log_area:
            self.log_area.AppendText(u'<{}:{}> {} 退出\n'.format(self.remote_ip, self.remote_port, self.username ))

    def on_file_sent(self, file):
        if self.log_area:
            self.log_area.AppendText(u'<{}:{}> {} 下载文件 {}\n'.format(self.remote_ip, self.remote_port, self.username, file ))

    def on_file_received(self, file):
        if self.log_area:
            self.log_area.AppendText(u'<{}:{}> {} 上传文件 {}\n'.format(self.remote_ip, self.remote_port, self.username, file))

    def on_incomplete_file_sent(self, file):
        if self.log_area:
            self.log_area.AppendText(u'<{}:{}> {} 下载不完整文件 {}\n'.format(self.remote_ip, self.remote_port, self.username, file))

    def on_incomplete_file_received(self, file):
        if self.log_area:
            self.log_area.AppendText(u'<{}:{}> {} 上传不完整文件 {}\n'.format(self.remote_ip, self.remote_port, self.username, file))

class FTPSeverThread(threading.Thread):
    def __init__(self, share_dir, user, passwd, ip, handler):
        threading.Thread.__init__(self)
        self.share_dir = share_dir
        self.user = user
        self.passwd = passwd
        self.ip = ip
        self.handler = handler
        self.server = None

    def close(self):
        if self.server is not None:
            self.server.close_all()

    def run(self):
        authorizer = DummyAuthorizer()
        authorizer.add_user(self.user, self.passwd, self.share_dir, perm='elrw')
        authorizer.add_anonymous(self.share_dir)

        self.handler.authorizer = authorizer
        self.handler.banner = 'Welcome Raisecom'

        self.server = FTPServer((self.ip, 21), self.handler)
        self.server.serve_forever()

class FTPServerPanel(wx.Panel):
    def __init__(self, parent=None):
        wx.Panel.__init__(self, parent=parent)
        self.CreateArea()

    def CreateArea(self):
        self.main_win = self
        self.ftp_thread = None
        self.CreateTopArea()
        self.CreateBottomArea()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.top_win, 0, wx.EXPAND)
        sizer.Add(self.bottom_win, 1, wx.EXPAND | wx.TOP, 5)
        self.main_win.SetSizer(sizer)

    def CreateTopArea(self):
        self.top_win = wx.Panel(self.main_win)
        self.file_btn = filebrowse.DirBrowseButton(self.top_win, labelText=u'①选择FTP目录:')

        header_text = wx.StaticText(self.top_win, label=u'②填写用户信息')
        user_st = wx.StaticText(self.top_win, label=u'用户:')
        self.user_tc = wx.TextCtrl(self.top_win, value='wrs')
        passwd_st = wx.StaticText(self.top_win, label=u'密码:')
        self.passws_tc = wx.TextCtrl(self.top_win, value=u'wrs')

        sizer_user = wx.BoxSizer(wx.HORIZONTAL)
        sizer_user.Add(header_text, 0, wx.EXPAND)
        sizer_user.Add(user_st, 0, wx.EXPAND | wx.LEFT, 5)
        sizer_user.Add(self.user_tc, 0, wx.EXPAND)
        sizer_user.Add(passwd_st, 0, wx.EXPAND | wx.LEFT, 5)
        sizer_user.Add(self.passws_tc, 0, wx.EXPAND)

        ip_st = wx.StaticText(self.top_win, label=u'③选择服务器IP:')
        choices = ["0.0.0.0"] + socket.gethostbyname_ex(socket.gethostname())[2]
        self.ip_choice = wx.Choice(self.top_win, choices=choices)
        sizer_ip = wx.BoxSizer(wx.HORIZONTAL)
        sizer_ip.Add(ip_st, 0, wx.EXPAND)
        sizer_ip.Add(self.ip_choice, 0, wx.EXPAND)

        create_btn = wx.Button(self.top_win, label=u'创建')
        create_btn.Bind(wx.EVT_BUTTON, self.CreateFTPServer, create_btn)

        stop_btn = wx.Button(self.top_win, label=u'停止')
        stop_btn.Bind(wx.EVT_BUTTON, self.StopFTPServer, stop_btn)

        sizer_thread = wx.BoxSizer(wx.HORIZONTAL)
        sizer_thread.Add(create_btn, 1, wx.EXPAND)
        sizer_thread.Add(stop_btn, 1, wx.EXPAND)

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.file_btn, 0, wx.EXPAND)
        sizer_main.Add(sizer_user, 0, wx.EXPAND)
        sizer_main.Add(sizer_ip, 0, wx.EXPAND)
        sizer_main.Add(sizer_thread, 0, wx.EXPAND)
        self.top_win.SetSizer(sizer_main)

    def CreateBottomArea(self):
        self.bottom_win = wx.Panel(self.main_win)
        sizer = wx.StaticBoxSizer(wx.VERTICAL, self.bottom_win, label=u'消息')
        self.log_area = wx.TextCtrl(self.bottom_win, style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(self.log_area, 1, wx.EXPAND)
        self.bottom_win.SetSizer(sizer)

    def StopFTPServer(self, evt):
        if self.ftp_thread and self.ftp_thread.is_alive():
            self.ftp_thread.close()
            self.log_area.AppendText('断开连接\n')

    def CreateFTPServer(self, evt):
        share_dir = self.file_btn.GetValue()
        username = self.user_tc.GetValue()
        password = self.passws_tc.GetValue()
        ip = self.ip_choice.GetStringSelection()

        if share_dir and username and password and ip:
            handler = MyHandler
            handler.timeout = 9600
            handler.log_area = self.log_area
            self.StopFTPServer(None)
            self.ftp_thread = FTPSeverThread(share_dir, username, password, ip, handler)
            self.ftp_thread.start()
            self.log_area.AppendText('创建成功\n')

    def RefreshChoice(self):
        origin_selection = self.ip_choice.GetSelection()
        self.ip_choice.Clear()
        choices = ["0.0.0.0"] + socket.gethostbyname_ex(socket.gethostname())[2]
        self.ip_choice.AppendItems(choices)
        self.ip_choice.SetSelection(origin_selection)

class TFTPSeverThread(threading.Thread):
    def __init__(self, share_dir, ip):
        threading.Thread.__init__(self)
        self.share_dir = share_dir
        self.ip = ip
        self.server = None
        self.create_success = None
        self.error_msg = None

    def close(self):
        if self.server is not None:
            self.server.stop(False)

    def run(self):
        try:
            self.server = tftpy.TftpServer(self.share_dir)
            self.server.listen()
        except socket.error as e:
            self.error_msg = e
            self.create_success = False

class TFTPServerPanel(wx.Panel):
    def __init__(self, parent=None):
        wx.Panel.__init__(self, parent=parent)
        self.CreateArea()

    def CreateArea(self):
        self.main_win = self
        self.tftp_thread = None
        self.CreateTopArea()
        self.CreateBottomArea()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.top_win, 0, wx.EXPAND)
        sizer.Add(self.bottom_win, 1, wx.EXPAND | wx.TOP, 5)
        self.main_win.SetSizer(sizer)
        self.Bind(wx.EVT_IDLE, self.OnIdle)

    def CreateTopArea(self):
        self.top_win = wx.Panel(self.main_win)
        self.file_btn = filebrowse.DirBrowseButton(self.top_win, labelText=u'①选择TFTP目录:')

        ip_st = wx.StaticText(self.top_win, label=u'③选择服务器IP:')
        choices = ["0.0.0.0"] + socket.gethostbyname_ex(socket.gethostname())[2]
        self.ip_choice = wx.Choice(self.top_win, choices=choices)
        sizer_ip = wx.BoxSizer(wx.HORIZONTAL)
        sizer_ip.Add(ip_st, 0, wx.EXPAND)
        sizer_ip.Add(self.ip_choice, 0, wx.EXPAND)

        create_btn = wx.Button(self.top_win, label=u'创建')
        create_btn.Bind(wx.EVT_BUTTON, self.CreateTFTPServer, create_btn)

        stop_btn = wx.Button(self.top_win, label=u'停止')
        stop_btn.Bind(wx.EVT_BUTTON, self.StopTFTPServer, stop_btn)

        sizer_thread = wx.BoxSizer(wx.HORIZONTAL)
        sizer_thread.Add(create_btn, 1, wx.EXPAND)
        sizer_thread.Add(stop_btn, 1, wx.EXPAND)

        sizer_main = wx.BoxSizer(wx.VERTICAL)
        sizer_main.Add(self.file_btn, 0, wx.EXPAND)
        sizer_main.Add(sizer_ip, 0, wx.EXPAND)
        sizer_main.Add(sizer_thread, 0, wx.EXPAND)
        self.top_win.SetSizer(sizer_main)

    def CreateBottomArea(self):
        self.bottom_win = wx.Panel(self.main_win)
        sizer = wx.StaticBoxSizer(wx.VERTICAL, self.bottom_win, label=u'消息')
        self.log_area = wx.TextCtrl(self.bottom_win, style=wx.TE_MULTILINE | wx.TE_READONLY)
        sizer.Add(self.log_area, 1, wx.EXPAND)
        self.bottom_win.SetSizer(sizer)

    def StopTFTPServer(self, evt):
        if self.tftp_thread and self.tftp_thread.is_alive():
            self.tftp_thread.close()
            self.log_area.AppendText('断开连接\n')

    def CreateTFTPServer(self, evt):
        share_dir = self.file_btn.GetValue()
        ip = self.ip_choice.GetStringSelection()
        if share_dir and ip:
            self.StopTFTPServer(None)
            self.tftp_thread = TFTPSeverThread(share_dir, ip)
            self.tftp_thread.start()
            self.log_area.AppendText('创建成功\n')

    def OnIdle(self, evt):
        if self.tftp_thread:
            if len(self.tftp_thread.server.sessions):
                for key, value in self.tftp_thread.server.sessions.iteritems():
                    if type(value).__name__ == 'TftpContextServer':
                        self.log_area.AppendText('{} Receive {}Bytes\n'.format(key, value.getBlocksize()))

            if  self.tftp_thread.create_success is False:
                self.log_area.AppendText('创建失败\n')
                error_msg = errorencode(self.tftp_thread.error_msg)
                self.log_area.AppendText(ftfy.fix_text(error_msg)+'\n')
                self.tftp_thread.create_success = None
                self.tftp_thread.error_msg = None

    def RefreshChoice(self):
        origin_selection = self.ip_choice.GetSelection()
        self.ip_choice.Clear()
        choices = ["0.0.0.0"] + socket.gethostbyname_ex(socket.gethostname())[2]
        self.ip_choice.AppendItems(choices)
        self.ip_choice.SetSelection(origin_selection)

class AppSettingReader(object):
    __root = None
    __tree = None

    def __init__(self, settingpath):
        self.path = settingpath

    def __enter__(self):
        if self.__root is None and self.__tree is None:
            parser = etree.XMLParser(encoding='utf-8', remove_blank_text=True, remove_comments=True)
            self.__tree = etree.parse(self.path, parser)
            self.__root = self.__tree.getroot()
            return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass

    def get(self, tag, key):
        node = self.__root.find(".//*[@name='{}']".format(tag))
        return node.attrib.get(key, None)

    def set(self, tag, attr):
        node = self.__root.find(".//*[@name='{}']".format(tag))
        node.attrib.update(attr)
        self.__tree.write(self.path, encoding='utf-8', pretty_print=True, xml_declaration=True)

#parse sequence xml file
class ParseSeqXML(object):
    def __init__(self, filepath):
        parser = etree.XMLParser(encoding='utf-8', remove_blank_text=True, remove_comments=True)
        self.tree = etree.parse(filepath, parser)
        self.root = self.tree.getroot()
        self._run = 'run'
        self.__serial_path = './serial'
        self.__options_path = './options'
        self.__runorder_path = './testtree'
        self.__order_path = './testitem'
        self.__attribute_path = './attribute'
        self.__tip_path = './tip'
        self.__assignversion = './assignversion'
        self.__meta = './meta'

    @classmethod
    def get_element_dict(cls, ele):
        if type(ele).__name__ !=  '_Element':
            raise TypeError('ERROR:ele is not an Element')
        D = dict(ele.attrib)
        for key, value in D.iteritems():
            if isinstance(value, basestring) and value.isdigit():
                D[key] = int(value)
        if D.has_key('timeout') and D['timeout'] == 'None':
            D['timeout'] = None
        return D

    #get serial setting in dictionary style
    def get_serial_setting(self):
        D = self.get_serial_element().attrib
        D_tmp = {}
        for key, value in D.iteritems():
            if isinstance(value, basestring) and value.isdigit():
                D_tmp[unicode(key)] = int(value)
        return D_tmp

    #get sequence name list
    def get_names(self):
        names_list = []
        for child in self.get_runorder_element().getchildren():
            names_list.append(child.tag)
        return names_list

    #get runorder and order in (runorder, order)  style
    def get_seq(self):
        seq = []
        for runorder in self.get_runorder_element().getchildren():
            for order in self.get_order_element().getchildren():
                if runorder.tag == order.tag:
                    seq.append((runorder, order))
        return seq

    #get element with xpath
    def get_element(self, xpath):
        return self.root.find(xpath)

    #get all element with xpath
    def get_all_element(self, xpath):
        return self.root.findall(xpath)

    #get options element
    def get_options_element(self):
        return self.root.find(self.__options_path)

    #get serial element
    def get_serial_element(self):
        return self.root.find(self.__serial_path)

    #get runorder element
    def get_runorder_element(self):
        return self.root.find(self.__runorder_path)

    #get order element
    def get_order_element(self):
        return self.root.find(self.__order_path)

    #get attribute element
    def get_attribute_element(self):
        return self.root.find(self.__attribute_path)

    #get tip elementf
    def get_tip_element(self):
        return self.root.find(self.__tip_path)

    #get assignversion element
    def get_assignversion_element(self):
        return self.root.find(self.__assignversion)

    #get meta element
    def get_meta_element(self):
        return self.root.find(self.__meta)


#manage microsoft aceess database
class AccessManager(object):
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_ins'):
            cls._ins = super(AccessManager, cls).__new__(cls, *args, **kwargs)
        return cls._ins

    def __init__(self, filename):
        #file name
        self.name = filename
        #connect mdb file
        if os.path.exists(self.name):
            # connect string
            conn_str = 'Driver={{{0}}};DBQ={1};'.format(pypyodbc.get_mdb_driver(), self.name)
            self.conn_db = pypyodbc.connect(conn_str)
        else:
            dirpath = os.path.dirname(self.name)
            if not os.path.exists(dirpath):os.makedirs(dirpath)
            self.conn_db = pypyodbc.win_create_mdb(self.name)
            self.create_table()

    #create 3 table we needed
    def create_table(self):
        sn_table_str = "create table sn_table(sn varchar(24), result varchar(100), starttime datetime, endtime datetime, totaltime varchar(100), operator varchar(100), \
            workorder varchar(100), bomcode varchar(100), productname varchar(100), productver varchar(100), lotno varchar(100), gud varchar(100), logserial memo, logprocess memo)"
        self.execute_sql(sn_table_str)

    #insert value to SN table
    def insert_sn(self, sn, result, starttime, endtime, totaltime, operator, workorder, bomcode, productname, productver, lotno, guid, logserial, logprocess):
        sql = 'insert into sn_table(sn, result, starttime, endtime, totaltime, operator, workorder, bomcode, productname, productver, lotno, gud, logserial, logprocess)' \
              ' VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        self.execute_sql(sql, (sn, result, starttime, endtime, totaltime, operator, workorder, bomcode, productname, productver, lotno, guid, logserial, logprocess))

    #excute sql statement
    def execute_sql(self, sql='', params=None, many_mode=False, call_mode=False):
        self.conn_db.cursor().execute(sql, params, many_mode, call_mode).commit()

    def close(self):
        self.conn_db.close()
        self.name = None

def AssignMesAttrBySN(mes_attr, main_logger ,ORACLE_CURSOR , SN):
    try:
        MES_ATTR = mes_attr
        strBarCode = MES_ATTR['extern_SN'] = SN
        extern_WJTableName = MES_ATTR['extern_WJTableName']
        WJTableName = 'DMSNEW.' + extern_WJTableName
        extern_AttempterCode = MES_ATTR['extern_AttempterCode']
        sql = "select repair, repair1, subid, qulity_flag, testposition, scan_type,scan_position  from " + \
              WJTableName + " where scan_time=(select max(scan_time) from " + \
              WJTableName + " where  barcode='" + strBarCode + "') and barcode='" + \
              strBarCode + "' order by scan_position desc,scan_type desc  ,subid desc"

        sql_value = ORACLE_CURSOR.execute(sql).fetchall()
    except KeyError as e:
        main_logger.error(errorencode(traceback.format_exc()))
        return False, u'工单为输入'
    except cx_Oracle.DatabaseError as e:
        main_logger.error(errorencode(traceback.format_exc()))
        return False, u'工单号不存在'

    if len(sql_value) != 0:
        MES_ATTR['extern_QualityFlag'] = mes_value(sql_value[0][3])
        MES_ATTR['extern_SubID'] = mes_value( sql_value[0][2])
        MES_ATTR['extern_ScanType'] = mes_value(sql_value[0][5])
        MES_ATTR['extern_repair'] = mes_value( sql_value[0][0])
        MES_ATTR['extern_repair1'] = mes_value(sql_value[0][1])
        MES_ATTR['extern_sn_testposition'] = mes_value(sql_value[0][4])
    else:
        MES_ATTR['extern_QualityFlag'] = 'no'
        MES_ATTR['extern_SubID'] = 0
        MES_ATTR['extern_ScanType'] = u'正常生产'
        MES_ATTR['extern_repair'] = u'未维修'
        MES_ATTR['extern_sn_testposition'] = u'未投产'

    work_done_status_sql = "select  COUNT(*)   from   DMSNEW.MTL_SUB_ATTEMPER   where   STATE <> '已完工'  AND  ATTEMPTER_CODE='{}' ".format(extern_AttempterCode)  # outer

    sql_value = ORACLE_CURSOR.execute(work_done_status_sql).fetchall()
    MES_ATTR['extern_work_done_status'] = mes_value( sql_value[0][0] )


    sql = "select SENDNO, SENDMPK from DMSNEW.WORK_MAIN_BARCODE where BARCODE='{}'".format(strBarCode)
    sql_value = ORACLE_CURSOR.execute(sql).fetchall()
    if  len(sql_value) == 0:
        MES_ATTR['extern_CompSendno'] = ''
        MES_ATTR['extern_CompSendmpk'] = ''
    else:
        MES_ATTR['extern_CompSendno'] = mes_value(sql_value[0][0])
        MES_ATTR['extern_CompSendmpk'] = mes_value(sql_value[0][1])

    return True, ''

def mes_check_is_notin_repair(mes_attr):
    MES_ATTR = mes_attr
    extern_QualityFlag = MES_ATTR['extern_QualityFlag']
    if extern_QualityFlag == 'yes':
        return False, u'此设备在维修状态'
    return True, ''

def mes_check_is_in_current_procedurce(appconfig, sn_value):
    mes_attr = appconfig['mes_attr']
    mes_cursor = appconfig['mes_cursor']
    extern_SubID = mes_attr['extern_SubID']
    extern_SerialNumber = mes_attr['extern_SerialNumber']
    extern_ScanType = mes_attr['extern_ScanType']
    extern_sn_testposition = mes_attr['extern_sn_testposition']
    equalNum = int(extern_SubID) - int(extern_SerialNumber)
    appconfig['available_sn'] =  get_available_sn(appconfig)
    if equalNum >= 0 and extern_ScanType == u'正常生产':
        return False, 'AfterStatin', u'该条码不在测试工序，该条码已过工序{}({})'.format(extern_SubID, extern_sn_testposition)
    elif equalNum < 0 and equalNum != -1:
        return False, 'BeforeStation',u'该条码不在测试工序，该条码已过工序{}({})'.format(extern_SubID, extern_sn_testposition)
    elif sn_value not in appconfig['available_sn']:
        return False, 'NoList' ,u'该条码{}不在测试列表中'.format(sn_value)
    else:
        sql = "select numr from dmsnew.work_main_barcode where barcode='{}'".format(sn_value)
        sql_value = mes_cursor.execute(sql).fetchone()
        if sql_value:
            odevity = sql_value[0]
            if odevity % 2 == 1:
                return False, 'Odd', u'该条码扫描次数为奇数{}'.format(odevity)
        return True, 'OK', ''

class SettingFrame(wx.Frame):
    def __init__(self, parent, title='', size=wx.DefaultSize, appconfig={}):
        wx.Frame.__init__(self, parent=parent, title=title, size=size)
        self.appconfig = appconfig
        self.SetIcon(wx.Icon(self.appconfig['iconpath']))
        self.main_panel = wx.Panel(self)
        self.statusbar = wx.StatusBar(self)
        self.SetStatusBar(self.statusbar)
        self.setting_file = self.appconfig['setting_file']
        self.tree = etree.parse(self.setting_file, common.parser_without_comments)
        self.root = self.tree.getroot()
        self.all_port_count = len(AvailablePort.get(all=True))
        self.disable_port_count = 0

        #显示方式--sizer
        viewer_sizer = self.viewer_sizer(self.main_panel)

        #协议
        protocol_sizer = self.protocol_sizer(self.main_panel)

        #串口设置
        if self.appconfig['protocol'] == 'serial':
            com_sizer = self.com_sizer(self.main_panel)
        elif  self.appconfig['protocol'] == 'telnet':
            com_sizer = (0, 0)
        else:
            com_sizer = (0, 0)

        #工单信息--sizer
        worktable_boxsizer = wx.StaticBoxSizer(wx.VERTICAL, self.main_panel, u"工单信息")
        worktable_sizer = self.worktable_sizer(self.main_panel)
        worktable_boxsizer.Add(worktable_sizer, 0, wx.EXPAND)

        #其他--sizer
        other_boxsizer = wx.StaticBoxSizer(wx.VERTICAL, self.main_panel, u"其他设置")

        aging_sizer = self.aging_time_sizer(self.main_panel)
        win_nums_sizer = self.win_nums_sizer(self.main_panel)
        other_boxsizer.Add(aging_sizer, 0, wx.EXPAND|wx.BOTTOM )
        other_boxsizer.Add(win_nums_sizer, 0, wx.EXPAND | wx.BOTTOM)
        checkitem_sizer = self.checkitem_sizer(self.main_panel)
        other_boxsizer.Add(checkitem_sizer, 0, wx.EXPAND)

        #
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        main_sizer.Add(viewer_sizer, 0, wx.EXPAND)
        main_sizer.Add(protocol_sizer, 0, wx.EXPAND)
        main_sizer.Add(com_sizer, 0, wx.EXPAND)
        main_sizer.Add(worktable_boxsizer , 0, wx.EXPAND)
        main_sizer.Add(other_boxsizer, 1, wx.EXPAND)
        self.main_panel.SetSizerAndFit(main_sizer)

    def protocol_sizer(self, main_panel):
        panel = main_panel
        box = wx.RadioBox(panel, -1, u'协议', choices=[u'Serial', u'Telnet'], name='protocol')
        if self.appconfig['protocol'] == 'serial':
            box.SetSelection(0)
        elif  self.appconfig['protocol'] == 'telnet':
            box.SetSelection(1)
        box.Bind(wx.EVT_RADIOBOX, self.OnProtocolSelect)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(box, 0, wx.EXPAND)
        return sizer

    def viewer_sizer(self, main_panel):
        panel = main_panel
        mode_box = wx.RadioBox(panel, -1, u'显示模式', choices=[u'单串口模式', u'双串口模式'], name='mode')
        mode_box.Bind(wx.EVT_RADIOBOX, self.OnModeSelect)
        mode_box.Enable(False)

        viewr_box = wx.RadioBox(panel, -1, u'MES区', choices=[ u'隐藏MES区', u'显示MES区'], name='viewer')
        viewr_box.Bind(wx.EVT_RADIOBOX, self.OnModeSelect)

        with AppSettingReader(self.appconfig['appsetting_file'])  as s:
            if s.get('mes_area', 'value') == 'hide':
                viewr_box.SetSelection(0)
            else:
                viewr_box.SetSelection(1)

            if s.get('mode', 'value') == 'single':
                mode_box.SetSelection(0)
            else:
                mode_box.SetSelection(1)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(mode_box, 0, wx.EXPAND)
        sizer.Add(viewr_box, 0, wx.EXPAND)
        return sizer


    def worktable_sizer(self, main_panel):
        panel = main_panel
        extern_StationCode =  self.appconfig['mes_attr']['extern_StationCode']
        extern_SubLineCode =  self.appconfig['mes_attr']['extern_SubLineCode']
        extern_WJTableName =  self.appconfig['mes_attr']['extern_WJTableName']

        size_ST = (-1, -1)
        size_TC = (150, -1)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        stationST = wx.StaticText(panel, -1, u'工序:', size=size_ST)
        stationTC = wx.TextCtrl(panel, -1, extern_StationCode, name="station", size=size_TC)

        lineST = wx.StaticText(panel, -1, u'线体:', size=size_ST)
        lineTC = wx.TextCtrl(panel, -1, extern_SubLineCode, name="line", size=size_TC)

        wjtST = wx.StaticText(panel, -1, u'工单号:', size=size_ST)
        wjtTC = wx.TextCtrl(panel, -1, extern_WJTableName, name="worktable", size=size_TC)

        sizer_station = wx.BoxSizer(wx.HORIZONTAL)
        sizer_station.Add(stationST, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer_station.Add(stationTC, 1, wx.GROW | wx.CENTER)

        sizer_line = wx.BoxSizer(wx.HORIZONTAL)
        sizer_line.Add(lineST, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer_line.Add(lineTC, 1, wx.GROW | wx.CENTER)

        sizer_wjt = wx.BoxSizer(wx.HORIZONTAL)
        sizer_wjt.Add(wjtST, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer_wjt.Add(wjtTC, 1, wx.GROW | wx.CENTER)

        sizer.Add(sizer_station, 0, wx.EXPAND|wx.RIGHT, 20)
        sizer.Add(sizer_line, 0, wx.EXPAND | wx.RIGHT, 20)
        sizer.Add(sizer_wjt, 0, wx.EXPAND | wx.RIGHT)

        stationTC.Bind(wx.EVT_TEXT, self.OnWorkTableText)
        lineTC.Bind(wx.EVT_TEXT, self.OnWorkTableText)
        wjtTC.Bind(wx.EVT_TEXT, self.OnWorkTableText)
        return sizer

    def checkitem_sizer(self, main_panel):
        panel = main_panel
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        one_pass_on_mes = wx.CheckBox(panel, -1, label=u'自动过站', name="one_pass")
        many_pass_on_mes = wx.CheckBox(panel, -1, label=u'批量过站', name="many_pass")

        one_pass_on_mes.Enable(False)
        many_pass_on_mes.Enable(False)
        sizer.Add(one_pass_on_mes, 0, wx.EXPAND | wx.RIGHT, 5)
        sizer.Add(many_pass_on_mes, 0, wx.EXPAND | wx.RIGHT, 5)

        one_pass_on_mes.Bind(wx.EVT_CHECKBOX, self.OnCheckBox)
        many_pass_on_mes.Bind(wx.EVT_CHECKBOX, self.OnCheckBox)
        return sizer

    def aging_time_sizer(self, main_panel):
        panel = main_panel
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        aging_text = wx.StaticText(panel, label=u"老化时间:")
        aging_spin = wx.SpinCtrl(panel, -1, '', min=0, max=120, initial=int( self.appconfig['agingtime']) )
        sizer.Add(aging_text, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 10)
        sizer.Add(aging_spin, 0, wx.EXPAND)
        aging_spin.Bind(wx.EVT_SPINCTRL, self.OnAgingTimeSet)
        aging_spin.Bind(wx.EVT_TEXT, self.OnAgingTimeSet)

        return sizer

    def win_nums_sizer(self, main_panel):
        panel = main_panel
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        nums_text = wx.StaticText(panel, label=u"窗口数量:")
        nums_spin = wx.SpinCtrl(panel, -1, '', min=1, max=90, initial= int( self.appconfig['initwinnum']) )
        sizer.Add(nums_text, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 10)
        sizer.Add(nums_spin, 0, wx.EXPAND)
        nums_spin.Bind(wx.EVT_SPINCTRL, self.OnWinNumsSet)
        nums_spin.Bind(wx.EVT_TEXT, self.OnWinNumsSet)

        return sizer

    def OnAgingTimeSet(self, evt):
        self.appconfig['agingtime'] = str(evt.GetInt() )
        self.statusbar.SetStatusText('老化时间：{}H'.format(evt.GetInt()))

    def OnWinNumsSet(self, evt):
        self.appconfig['initwinnum'] = str( evt.GetInt() )
        self.statusbar.SetStatusText('窗口数量：{}'.format(evt.GetInt()))

        with AppSettingReader(self.appconfig['appsetting_file'])  as s:
            s.set('initwinnum', {'value': str(evt.GetInt())})

    #创建com sizer布局器
    def com_sizer(self, main_panel):
        com_sizer = wx.StaticBoxSizer(wx.VERTICAL, main_panel, u"COM端口设置")
        for com in AvailablePort.get(all=True):
            panel = self.create_com_sizer_item(self.main_panel, com)
            com_sizer.Add(panel, 0, wx.EXPAND | wx.BOTTOM, 5)

        return com_sizer

    def create_com_sizer_item(self, main_panel, which_com):
        port_pair = [which_com,'name', which_com, which_com, 0, (40, -1)]
        stopbit_pair = (which_com,'stopbits', '停止位:', ['1', '2'], 0, (40, -1))
        databit_pair = (which_com,'bytesize', '数据位:', ['5', '6', '7', '8'], 3, (40, -1))
        parity_pair = (which_com,'parity', '校验位:', ['N', 'E', 'O', 'S', 'M'], 0, (40, -1))
        baudrate_pair = (which_com,'baudrate', '波特率:', ['9600', '115200'], 0, (70, -1))

        panel = wx.Panel(main_panel, name="{0}-{0}".format(which_com))
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        node = self.root.find(".//port[@name='{}']".format(which_com))
        for com, name, text, choices, default_sel, csize in [port_pair, stopbit_pair, databit_pair, parity_pair, baudrate_pair]:
            cname = '{}-{}'.format(com, name)
            if name == "name":
                com_checkbox = wx.CheckBox(panel, label=unicode(text), name=cname)
                com_checkbox.SetValue( True if node.get('enable')== "False" else False )
                if node.get('enable')== "False" :
                    self.disable_port_count += 1
                    panel.SetBackgroundColour(COLOUR_GRAY)
                else:
                    panel.SetBackgroundColour(COLOUR_WHITE)

                com_checkbox.Bind(wx.EVT_CHECKBOX, self.OnCOMCheckBox)
                sizer.Add(com_checkbox, 0, wx.ALIGN_BOTTOM | wx.RIGHT, 5)
            else:
                label = wx.StaticText(panel, label=unicode(text))
                choice = wx.Choice(panel, choices=choices, size=csize, name=cname)
                choice.Bind(wx.EVT_CHOICE, self.OnChoice)
                choice.SetSelection(choices.index(node.get(name)))
                tsizer = wx.BoxSizer(wx.HORIZONTAL)
                tsizer.Add(label, 0, wx.ALIGN_BOTTOM | wx.RIGHT, 3)
                tsizer.Add(choice, 0, wx.ALIGN_BOTTOM | wx.RIGHT)
                sizer.Add(tsizer, 0, wx.ALIGN_BOTTOM|wx.RIGHT, 15)

        panel.SetSizer(sizer)
        return panel

    def OnCheckBox(self, evt):
        obj = evt.GetEventObject()
        obj_name = obj.GetName()
        obj_label = obj.GetLabel()

        if obj_name == "one_pass":
            self.appconfig['mes_switch'] = evt.IsChecked()
        elif obj_name == "many_pass":
            self.appconfig['flow_switch'] = evt.IsChecked()

        if evt.IsChecked():
            self.statusbar.SetStatusText(u'使能 {} 标记'.format(obj_label))
        else:
            self.statusbar.SetStatusText(u'禁用 {} 标记'.format(obj_label))

    def OnCOMCheckBox(self, evt):
        obj = evt.GetEventObject()
        com_name, com_attr = obj.GetName().split('-')
        parent = obj.GetParent()

        if evt.IsChecked():
            self.disable_port_count += 1
            parent.SetBackgroundColour(COLOUR_GRAY)
            self.statusbar.SetStatusText(u'禁用{}端口,端口禁用后重启软件生效'.format(com_name))
        else:
            self.disable_port_count -= 1
            parent.SetBackgroundColour(COLOUR_WHITE)
            self.statusbar.SetStatusText(u'使能{}端口，端口使能后重启软件生效'.format(com_name))

        if self.disable_port_count == self.all_port_count:
            obj.SetValue(False)
            self.disable_port_count -= 1
            parent.SetBackgroundColour(COLOUR_WHITE)
            self.statusbar.SetStatusText(u'不能禁用所有窗口')

        parent.Refresh()
        node = self.root.find(".//port[@name='{}']".format(com_name))
        node.set('enable', str( not evt.IsChecked()) )
        self.tree.write(self.setting_file, encoding='utf-8', pretty_print=True, xml_declaration=True)

    def OnChoice(self, evt):
        obj = evt.GetEventObject()
        com_name, com_attr = obj.GetName().split('-')
        attr_value = evt.GetString()
        node = self.root.find(".//port[@name='{}']".format(com_name))
        node.set(com_attr, attr_value)
        self.tree.write(self.setting_file, encoding='utf-8', pretty_print=True, xml_declaration=True)
        serial_attr = ParseSeqXML.get_element_dict(node)
        all_coms = AvailablePort.get()
        pub.sendMessage(TOPIC_PORT_SET, setting_value=serial_attr, win_idx=all_coms.index(com_name))

    def OnWorkTableText(self, evt):
        obj = evt.GetEventObject()
        obj_name = obj.GetName()
        obj_value = evt.GetString().upper().strip()
        if obj_name == "station":
            self.appconfig['mes_attr']['extern_StationCode'] = obj_value
        elif obj_name == "line":
            self.appconfig['mes_attr']['extern_SubLineCode'] = obj_value
        elif obj_name == "worktable":
            self.appconfig['mes_attr']['extern_WJTableName'] = obj_value

        worksql_value, linesql_value, stasql_value, tipmsg = query_linestation_info(self.appconfig)
        assign_status, assign_msg = assignMesAttr(self.appconfig)
        if not (worksql_value and linesql_value and stasql_value and assign_status ):
            tipmsg += assign_msg
            self.statusbar.SetStatusText(tipmsg)
        else:
            self.statusbar.SetStatusText(u'工单信息输入正确')

    def OnModeSelect(self, evt):
        obj = evt.GetEventObject()
        obj_name = obj.GetName()
        self.statusbar.SetStatusText(evt.GetString())

        with AppSettingReader(self.appconfig['appsetting_file'])  as s:
            if obj_name == 'mode':
                if evt.GetSelection() == 0:
                    s.set('mode', {'value': 'single'})
                else:
                    s.set('mode', {'value': 'double'})

            if obj_name == 'viewer':
                main_frame = wx.Window.FindWindowByName('MainFrame')
                main_win = main_frame.main_window
                test_win = main_frame.test_window
                mes_win = main_frame.mes_window
                if evt.GetSelection() == 0:
                    main_win.Unsplit(mes_win)
                    s.set('mes_area', {'value': 'hide'})
                else:
                    main_win.SplitVertically(mes_win, test_win)
                    s.set('mes_area', {'value': 'show'})

    def OnProtocolSelect(self, evt):
        with AppSettingReader(self.appconfig['appsetting_file'])  as s:
            s.set('protocol', {'value': evt.GetString().lower()})
            self.statusbar.SetStatusText('设置重启后生效'.format(evt.GetInt()))


