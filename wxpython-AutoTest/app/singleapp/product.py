# coding=utf-8
import wx
import wx.lib
import os
import re
import time
import threading
import sys
import traceback
from datetime import datetime
import binascii
import pandas as pd
import wx.lib.newevent
from lxml import etree
from ..common import communicate
from ..common import feature
from ..common.feature import errorencode
from ..common.feature import PASS, FAIL, ERROR
reload(sys)
sys.setdefaultencoding('utf-8')
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'
############################单串口版##############################
#main process call product run method as a thread
#const value
#colour
COLOUR_RED = wx.Colour(249, 0, 0)
COLOUR_GREEN = wx.Colour(0, 249, 0)
COLOUR_YELLOW = wx.Colour(239, 249, 49)
COLOUR_WHITE = wx.Colour(255, 255, 255)
COLOUR_BLACK = wx.Colour(0, 0, 0)
COLOUR_GRAY = wx.Colour(127, 127, 127)
COLOUR_AQUA = wx.Colour(32,178,170)

COLOUR_RESUME = COLOUR_START = COLOUR_AQUA
COLOUR_PAUSE = COLOUR_YELLOW
COLOUR_PASS = COLOUR_GREEN
COLOUR_STOP = COLOUR_FAIL = COLOUR_RED
THREAD_LOCK = threading.RLock()

#通知主线程弹出对话框
(ThreadDialogEvent, EVT_THREAD_DIALOG) = wx.lib.newevent.NewEvent()
#线程结束时通知主线程
(ThreadDeathEvent, EVT_THREAD_DEATH) = wx.lib.newevent.NewEvent()

def utf8i(cstr):
    return  str(cstr).decode('utf-8', 'ignore')

def mes_value(value):
    mes_value =  '' if value == None else unicode(value)
    return mes_value

class Product(object):
    def __init__(self, product_dict, data_queue, appconfig , win):
        self.appconfig = appconfig
        #页窗口
        self.win = win
        #设备窗口
        self.dev_win = self.win.dev_win
        #窗口名称
        self.name = win.name
        #窗口编号
        self.win_idx = win.win_idx
        #窗口设备
        self.dev = None
        #设备信息输出域
        self.log_area = self.win.log_area
        #流程信息域
        self.section_log = self.win.message_win.section_window.section_log
        #产品字典
        self.dict = product_dict
        #SN label
        self.sn_text = self.dev_win.sn_text
        #name label
        self.name_text = self.dev_win.name_text
        #状态 label
        self.status_text = self.dev_win.status_text
        #linefeed
        self.linefeed = None
        #hostword
        self.host = None
        #exit cmd
        self.exitcmd = None
        #options
        self.options = None
        #mes database cursor and connect
        self.mes_cursor = self.appconfig['mes_cursor']
        self.mes_conn = self.appconfig['mes_conn']
        #log store cursor and db
        self.log_conn = self.appconfig['log_conn']
        self.log_cursor = self.appconfig['log_cursor']
        self.logger = self.appconfig['logger']
        #attribute to control self mission
        self.__condition = threading.Condition()
        self.__pause = False
        self.__keepgoing = False
        self.product_name = None
        self.xml =None
        self.meta = None
        self.data_queue = data_queue
        self.popupobj =  self.appconfig['popupobj']
        self.mes_switch = self.appconfig['mes_switch'] #MES 记录以MES方式写入数据库，PASS时自动过站；
        self.workstage_flag = self.appconfig['workstage_flag']
        self.mes_attr = self.appconfig['mes_attr']
        self.process_handle = self.appconfig['process_handle']
        #第二波特率
        self.second_baudrate = None
        #第二端口, telnet专用
        self.second_port = None
        #根据SN获取组装绑定关系
        self.bind_info = None

    def postclose(self):
        wx.CallAfter(self.name_text.SetLabel, '{}'.format(self.name) )
        try:
            if self.dev and self.dev.alive(): self.dev.close()
            if self.meta and self.meta.get('filetype') == 'telnet':
                self.name = '{}:{}'.format(self.meta.get('ip'), self.second_port)
                self.win.dev = communicate.communicate_factory('telnet', **self.meta)
                if not self.win.dev.alive():
                    self.win.dev.connect()
            elif self.xml:
                serial_settings = self.xml.get_serial_setting()
                serial_settings.update({'port': self.name, 'baudrate': self.second_baudrate})
                self.win.dev.apply_settings(**serial_settings)
                if not self.win.dev.alive():
                    self.win.dev.connect()

        except Exception as e:
            self.logger.error(errorencode(traceback.format_exc()) )
        self.popupobj[self.name].update({'isRunning': False})
        wx.CallAfter(self.dev_win.Refresh)

    #do after work
    def close(self, start_time, end_time, diff_time, result ):
        try:
            if self.mes_switch and result == PASS:
                ret = self.mes_write_ok(PASS)
                self.write_record_to_database(start_time, end_time, diff_time, result)
            else:
                self.write_record_to_database(start_time, end_time, diff_time, result, withmesfeature=False)
        finally:
            evt = ThreadDeathEvent(mes_attr=self.mes_attr, product_dict=self.dict, mes_switch=self.mes_switch, result=result)
            self.color_change_by_test_result(result)
            wx.PostEvent(self.win, evt)

    #stop mission
    def stop(self):
        with self.__condition:
            self.__keepgoing = False

    def enter_normal_mode(self, item=None):
        info = ''
        username = self.options.get('username')
        passwd = self.options.get('password')
        istimeout = False
        timeout = float(self.get_tag_value(item, 'timeout', '100'))
        nullfeed = self.get_tag_value(item, 'nullfeed', None)
        self.recored_process(content=sys._getframe().f_code.co_name, type="mode_in")
        self.write_cmd(self.linefeed)
        start_time = time.time()
        self.dev.set_read_timeout(1)
        while True:
            line = self.dev.read_line( fix=True)
            line = self.log_message(line)
            info += line

            if not self.__keepgoing or time.time() - start_time > timeout:
                istimeout = True
                break

            if re.match('^(login|username):', line, re.I):
                if re.match('^(login|username):\s*.*[\r\n]+', line, re.I):
                    continue
                else:
                    self.write_cmd(username + self.linefeed)
            elif re.match('password:', line, re.I):
                if re.match('password:\s*.*[\r\n]+', line, re.I):
                    self.write_cmd(self.linefeed)
                else:
                    self.write_cmd(passwd + self.linefeed)
            elif re.match('{}>'.format(self.host), line, re.I):
                break
            elif re.match('{}[^\r\n]+'.format(self.host), line, re.I):
                self.write_cmd(self.exitcmd + self.linefeed)
            elif line == '':
                if nullfeed == 'True':
                    self.write_cmd(self.linefeed)
                else:
                    continue
        self.recored_process(content=sys._getframe().f_code.co_name, type="mode_out")
        return info, istimeout

    def enter_super_mode(self, item=None):
        info = ''
        username = self.options.get('username')
        passwd = self.options.get('password')
        super_cmd = self.options.get('super_cmd')
        timeout =  float( self.get_tag_value(item, 'timeout', '100') )
        nullfeed = self.get_tag_value(item, 'nullfeed', 'True')
        self.recored_process(content=sys._getframe().f_code.co_name, type="mode_in")
        self.write_cmd(self.linefeed)
        istimeout = False
        start_time = time.time()
        self.dev.set_read_timeout(1)
        while True:
            line = self.dev.read_line(fix=True)
            line = self.log_message(line)
            info += line
            if not self.__keepgoing or time.time() - start_time > timeout:
                istimeout = True
                break

            if re.match('{}>'.format(self.host), line, re.I):
                if re.match('{}>\s*{}[\r\n]+'.format(self.host, super_cmd), line, re.I):
                    self.write_cmd(passwd + self.linefeed)
                else:
                    self.write_cmd(super_cmd + self.linefeed)
            elif re.match('{}#'.format(self.host), line, re.I):
                if re.match('{}#\s*{}[\r\n]+'.format(self.host, self.exitcmd),  line, re.I):
                    self.write_cmd(self.linefeed)
                else:
                    break
            elif re.match('^(login|username):', line, re.I):
                if re.match('^(login|username):\s*.*[\r\n]+', line, re.I):
                    continue
                else:
                    self.write_cmd(username + self.linefeed)
            elif re.match('password:', line, re.I):
                if re.match('password:\s*.*[\r\n]+', line, re.I):
                    self.write_cmd(self.linefeed)
                else:
                    self.write_cmd(passwd + self.linefeed)
            elif re.match('{}[^\r\n]+'.format(self.host), line, re.I):
                if re.match('{}.+exit'.format(self.host), line, re.I ):
                    continue
                else:
                    self.write_cmd(self.exitcmd + self.linefeed)
            elif line == '':
                if nullfeed == 'True':
                    self.write_cmd(self.linefeed)
                else:
                    continue

        self.recored_process(content=sys._getframe().f_code.co_name, type="mode_out")
        return  info, istimeout

    def enter_debug_mode(self, item=None):
        info = ''
        debugcmd = self.options.get('debug_cmd')
        username = self.options.get('username')
        passwd = self.options.get('password')
        super_cmd = self.options.get('super_cmd')

        istimeout = False
        start_time = time.time()
        timeout = float(self.get_tag_value(item, 'timeout', '100'))
        nullfeed = self.get_tag_value(item, 'nullfeed', 'True')
        self.recored_process(content=sys._getframe().f_code.co_name, type="mode_in")
        self.write_cmd(self.linefeed)
        self.dev.set_read_timeout(1)
        while True:
            line = self.dev.read_line( fix=True)
            line = self.log_message(line)
            info += line

            if not self.__keepgoing or time.time() - start_time > timeout:
                istimeout = True
                break

            if re.match('{}>'.format(self.host), line, re.I):
                if re.match('{}>\s*{}[\r\n]+'.format(self.host, super_cmd), line, re.I):
                    self.write_cmd(passwd + self.linefeed)
                else:
                    self.write_cmd(super_cmd + self.linefeed)
            elif re.match('{}\(debug\)#'.format(self.host), line, re.I):
                if re.match('{}\(debug\)#\s*{}[\r\n]+'.format(self.host, self.exitcmd), line, re.I):
                    self.write_cmd(self.linefeed)
                else:
                    break
            elif re.match('{}#'.format(self.host), line, re.I):
                if  re.match('{}#\s*{}[\r\n]+'.format(self.host, debugcmd), line, re.I):
                    self.write_cmd(self.linefeed)
                else:
                    self.write_cmd(debugcmd + self.linefeed)
            elif re.match('^(login|username):', line, re.I):
                if re.match('^(login|username):\s*.*[\r\n]+', line, re.I):
                    continue
                else:
                    self.write_cmd(username + self.linefeed)
            elif re.match('password:', line, re.I):
                if re.match('password:\s*.*[\r\n]+', line, re.I):
                    self.write_cmd(self.linefeed)
                else:
                    self.write_cmd(passwd + self.linefeed)
            elif re.match('{}[^\r\n]+'.format(self.host), line, re.I):
                self.write_cmd(self.exitcmd + self.linefeed)
            elif line == '':
                if nullfeed == 'True':
                    self.write_cmd(self.linefeed)
                else:
                    continue
        self.recored_process(content=sys._getframe().f_code.co_name, type="mode_out")
        return  info, istimeout

    def enter_config_mode(self, item=None):
        info = ''
        configcmd = self.options.get('config_cmd')
        username = self.options.get('username')
        passwd = self.options.get('password')
        super_cmd = self.options.get('super_cmd')

        istimeout = False
        start_time = time.time()
        timeout = float(self.get_tag_value(item, 'timeout', '100'))
        nullfeed = self.get_tag_value(item, 'nullfeed', 'True')
        self.recored_process(content=sys._getframe().f_code.co_name, type="mode_in")
        self.write_cmd(self.linefeed)
        self.dev.set_read_timeout(1)
        while True:
            line = self.dev.read_line(fix=True)
            line = self.log_message(line)
            info += line

            if not self.__keepgoing or time.time() - start_time > timeout:
                istimeout = True
                break

            if re.match('{}>'.format(self.host), line, re.I):
                if re.match('{}>\s*{}[\r\n]+'.format(self.host, super_cmd), line, re.I ):
                    self.write_cmd(passwd + self.linefeed)
                else:
                    self.write_cmd(super_cmd + self.linefeed)
            elif re.match('{}\(config\)#'.format(self.host), line, re.I):
                if re.match('{}\(config\)#\s*{}[\r\n]+'.format(self.host, self.exitcmd), line, re.I):
                    self.write_cmd(self.linefeed)
                else:
                    break
            elif re.match('{}#'.format(self.host), line, re.I):
                if  re.match('{}#\s*{}[\r\n]+'.format(self.host, configcmd), line, re.I):
                    self.write_cmd(self.linefeed)
                else:
                    self.write_cmd(configcmd + self.linefeed)
            elif re.match('^(login|username):', line, re.I):
                if re.match('^(login|username):\s*.*[\r\n]+', line, re.I):
                    continue
                else:
                    self.write_cmd(username + self.linefeed)
            elif re.match('password:', line, re.I):
                if re.match('password:\s*.*[\r\n]+', line, re.I):
                    self.write_cmd(self.linefeed)
                else:
                    self.write_cmd(passwd + self.linefeed)
            elif re.match('{}[^\r\n]+'.format(self.host), line, re.I):
                self.write_cmd(self.exitcmd + self.linefeed)
            elif line == '':
                if nullfeed == 'True':
                    self.write_cmd(self.linefeed)
                else:
                    continue

            if time.time() - start_time > timeout and self.__keepgoing:
                istimeout = True
                break
        self.recored_process(content=sys._getframe().f_code.co_name, type="mode_out")
        return info, istimeout

    def log_message(self, line):
        line = re.sub(r'[\n]{1,}', '\n', line)
        try:
            wx.CallAfter(self.log_area.AppendText, line)
            self.recored_process(content=line, type="echo")
        except wx.PyAssertionError as e:
            self.logger.error(errorencode(traceback.format_exc()) )
            self.section_message(u'软件检测到错误，请重新启动', True)
        return line

    # data = ('stage', 'result', 'start_time', 'end_time')
    def section_message(self, data, showcolor=False):
        message = ''
        if isinstance(data, tuple):
            stage, result = data[0], data[1]
            start_time, end_time = data[2], data[3]
            diff_time = data[4]
            message = u'{:30s}\t{}\t{}\t{}\t{}s'.format(stage, result, start_time, end_time, diff_time)
            wx.CallAfter(self.section_log.AppendText, message + '\n')
            if result == FAIL: showcolor=True
        elif isinstance(data, basestring):
            message = data
            wx.CallAfter(self.section_log.AppendText, message + '\n')

        if showcolor:
            # start_pos = self.section_log.GetValue().find(message)
            # end_pos = start_pos + len(message)
            text_attr = wx.TextAttr(wx.Colour(255, 0, 0), wx.Colour(255, 255, 255))
            pos_list = self.find_pos(message, self.section_log.GetValue(), self.section_log.GetValue())
            for start_pos, end_pos in pos_list:
                wx.CallAfter(self.section_log.SetStyle, start_pos, end_pos, text_attr)

    #第一次测试时显示提示信息
    def show_tip_msg(self, product_xml):
        if not self.appconfig['tip_once']['hadrun']:
            msg = ''
            tip_node = product_xml.get_tip_element()
            if tip_node == None: return
            for child in tip_node.getchildren():
                if child.get('station') == self.appconfig['station_name']:
                    msg += child.get('value') + '\n'
            wx.MessageBox(msg, u'提示')
            self.appconfig['tip_once']['hadrun'] = True

    def get_assign_version(self, xml, mes_attr):
        assignversion_ele = xml.get_assignversion_element()
        if assignversion_ele is None: return True, ''
        try:
            extern_WJTableName = mes_attr['extern_WJTableName']
            extern_StationName = mes_attr['extern_StationName']
            sql = "select filename  from DMSNEW.tab_productsubsoftware_history w where w.WORKJOB_CODE='{}' and w.realtestposition ='{}' and  w.createdate = (SELECT MAX(CREATEDATE) FROM \
                  DMSNEW.tab_productsubsoftware_history w where w.WORKJOB_CODE='{}' and w.realtestposition ='{}')".format( extern_WJTableName, extern_StationName, extern_WJTableName, extern_StationName)
            filenams_list = self.mes_cursor.execute(sql).fetchall()
            df = pd.DataFrame(filenams_list, columns=['filename'])
            for child in assignversion_ele.iterchildren():
                for filename in df.values:
                    match = re.search(child.get('regex', ''), filename[0])
                    if match and len(match.groups()) > 0:
                        self.dict[child.get('assign', 'NULL')] = match.groups()[0]
                        break
                    self.dict[child.get('assign', 'NULL')] = child.get('default', 'NULL')
        except KeyError as e:
            return False, '未录入工单号，不能获取工单信息'
        return True, ''

    def check_mac_is_used(self, sn_value ,mac_value):
        #rel_item 形式('103002027500S17C28S0001D', 'C8:50:E9:6E:40:74', 'C8:50:E9:6E:40:75', '000E5E-001730S17C27S0010')
        if self.appconfig['worktable_loaded']:
            if self.bind_info is not None:
                if mac_value == self.bind_info[1]:
                    return True
                else:
                    tip_msg = '扫入：{}\n组装绑定记录为：{}'.format(mac_value, self.bind_info[1])
                    dlg = wx.MessageDialog(self.win, tip_msg, u'{}：{}警告'.format(self.name, sn_value), style=wx.OK | wx.CANCEL | wx.CENTER | wx.ICON_WARNING)
                    dlg.SetOKCancelLabels(u'继续测试', u'取消测试')
                    return True if dlg.ShowModal() == wx.ID_OK else False
            else:
                tip_msg = '组装SN:{}\nMAC:{}无绑定关系'.format(sn_value, mac_value)
                dlg = wx.MessageDialog(self.win, tip_msg, u'{}：{}警告'.format(self.name, sn_value), style=wx.OK | wx.CANCEL | wx.CENTER | wx.ICON_WARNING)
                dlg.SetOKCancelLabels(u'继续测试', u'取消测试')
                return True if dlg.ShowModal() == wx.ID_OK else False
        else:
            sql = "select distinct sn, segment1 from raisecom.sn_table where segment1=\"{}\"".format(mac_value)
            ret_rows = self.log_cursor.execute(sql)
            sql_rows = self.log_cursor.fetchall()
            if ret_rows:
                bind_sn_list = []
                for sn, mac in sql_rows:
                    bind_sn_list.append(sn)

                bind_sn_str = '\n'.join(bind_sn_list)
                if len(bind_sn_list) == 1:
                    return True
                dlg = wx.MessageDialog(self.win, u'{}已使用\n绑定的SN为\n{}'.format(mac_value, bind_sn_str),  u'{}:MAC已使用'.format(self.name), style=wx.OK | wx.CANCEL | wx.CENTER)
                dlg.SetOKCancelLabels(u'继续测试', u'取消测试')
                if dlg.ShowModal() == wx.ID_OK:
                    return True
                else:
                    return False
            else:
                return True

    def prepare(self):
        evt = ThreadDialogEvent(win_idx=self.win_idx, type='SN', data={'win':self.win})
        wx.PostEvent(self.win, evt)
        status, sn_value = self.data_queue.get()
        if not status: return False

        if self.appconfig['worktable_had_changed']:
            self.appconfig['worktable_had_changed'] = False
            self.xml, self.product_name = feature.getProductXML(self.appconfig['ftp_base_config_dir_anonymous'], subproduct=self.mes_attr.get('workjob_review', 'default'), sn=sn_value)
            self.appconfig['product_xml'] =  self.xml, self.product_name
        else:
            self.xml, self.product_name = self.appconfig.get('product_xml')

        if self.xml is None:
            self.appconfig['worktable_had_changed'] = True
            self.section_message(u'在 ftp://192.168.60.70/AutoTest-Config/config.xml 中无该SN配置项', showcolor=True)
            return False

        self.options = self.xml.get_options_element().attrib
        self.host = self.get_tag_value(self.options, 'hostword', 'raisecom')
        self.exitcmd = self.get_tag_value(self.options, 'exit_cmd', 'quit')
        self.linefeed = self.get_tag_value(self.options, 'linefeed', '\n')

        if self.xml.get_meta_element() is not None:
            self.meta = self.xml.get_meta_element().attrib

        #Telnet 类型更新窗口
        if self.meta and self.meta.get('filetype') == 'telnet':
            self.name = '{}:{}'.format(self.meta.get('ip'), self.meta.get('port') )
            self.win.name = self.name
            notebook = self.win.GetParent()
            notebook.SetPageText(self.win_idx, self.name)
            self.name_text.SetLabel(self.name)
            self.dev_win.Refresh()
            if not  self.popupobj.has_key(self.name):
                self.popupobj[self.name] = {'auto_popup': self.appconfig['popup_sn_flag']}


        #获取绑定信息
        self.bind_info = feature.get_bind_info_by_barcode(self.appconfig, sn_value)
        customer_sn_value = self.get_customer_sn_value()

        if self.appconfig['worktable_loaded']:
            assign_status, assign_msg = feature.AssignMesAttrBySN(self.mes_attr, self.logger, self.mes_cursor, sn_value)
            if self.appconfig['repaire_mode'] is False:
                repair_status, repair_msg = feature.mes_check_is_notin_repair(self.mes_attr)
                use_status, use_status_code ,use_msg = feature.mes_check_is_in_current_procedurce(appconfig=self.appconfig, sn_value=sn_value)
                if not (assign_status and repair_status and use_status):
                    msg = assign_msg + repair_msg + use_msg
                    self.section_message(msg, showcolor=True)
                    if use_status_code == 'AfterStatin':
                        dlg = wx.MessageDialog(self.win, '该条码{}已过站'.format(sn_value), u'{}:已过站'.format(self.name), style=wx.OK | wx.CANCEL | wx.CENTER|wx.ICON_WARNING)
                        dlg.SetOKCancelLabels(u'重测', u'取消')
                        if dlg.ShowModal() == wx.ID_CANCEL:
                            return False
                    else:
                        return False

        #根据工单 获取软件软件信息
        status, msg = self.get_assign_version(self.xml, self.mes_attr)
        if not status:
            self.section_message(msg, showcolor=True)
            return False

        if self.workstage_flag or self.appconfig['workstage_popup_once_flag']:
            status, workstage_value = self.choose_workstage(self.xml)
            if not status:
                return False
            else:
                self.appconfig['workstage_popup_once_flag'] = False
                self.appconfig['station_name'] = str(workstage_value)

        if not self.workstage_msgbox(self.appconfig['station_name'], self.xml): return False

        if self.meta and self.meta.get('filetype') == 'telnet':
            self.name = '{}:{}'.format(self.meta.get('ip'), self.second_port)
            self.win.name = self.name
            notebook = self.win.GetParent()
            notebook.SetPageText(self.win_idx, self.name)
            self.name_text.SetLabel(self.name)
            self.dev_win.Refresh()

            self.win.dev.close()
            self.dev = communicate.communicate_factory('telnet', **self.meta)
            self.dev.connect()
        else:
            self.win.dev.close()
            serial_settings = self.xml.get_serial_setting()
            serial_settings.update({'port': self.name, 'baudrate': self.second_baudrate})
            self.dev = communicate.communicate_factory('serial', **serial_settings)
            self.dev.connect()

        # get attribute in xml and place in procut_dict
        for key, value in self.mes_attr.iteritems():
            if key.startswith('@'):
                self.dict.update({key: value})

        if self.xml.get_attribute_element() is not None:
            for item in self.xml.get_attribute_element():
                if item.attrib.has_key('station') and self.get_tag_value(item, 'station') == self.appconfig['station_name']:
                    self.dict[item.get('name')] = self.get_tag_value(item, 'value')
                elif not item.attrib.has_key('station'):
                    self.dict[item.get('name')] = self.get_tag_value(item, 'value')

        self.show_tip_msg(self.xml)
        wx.CallAfter(self.section_log.Clear)
        wx.CallAfter(self.log_area.Clear)
        self.process_handle.truncate(0)
        self.process_handle.seek(0)
        now = datetime.now()
        password5508 = str(now.year + now.month * now.day)
        self.dict.update({'@SN': sn_value.upper(), '@CSN':customer_sn_value.upper() , '@PASSWORD5508':password5508, '@NAME':self.name.upper()})
        return True

    def workstage_msgbox(self, station_name='', xml='', sn_value=''):
        node = xml.root.find("./workstage/*[@value='{}']".format(station_name))
        if node is None: return True
        show_mac = node.get('show_mac', 'True')
        pass_station = node.get('pass_station', 'False')
        default_baudrate = self.xml.get_serial_element().get('baudrate', '9600')
        self.second_baudrate = node.get('baudrate', default_baudrate)
        if self.meta:
            self.second_port = node.get('port', self.meta.get('port'))
        self.appconfig['show_mac'] = True  if show_mac == 'True' else False

        #弹出MAC框
        if self.appconfig['show_mac'] :
            evt = ThreadDialogEvent(win_idx = self.win_idx, type='MAC', data={'win':self.win})
            wx.PostEvent(self.win, evt)
            status, mac_value = self.data_queue.get()
            if not status: return False
            mac_value = mac_value.upper().strip()
            if not self.check_mac_is_used(sn_value, mac_value): return False
        else:
            mac_value = "00:00:00:00:00:00"

        self.dict.update({'@MAC': mac_value.upper()})
        self.dict.update(feature.macAddrCreator(mac_value))

        #过站
        self.mes_switch = True if pass_station == 'True' else False
        if self.appconfig['repaire_mode']:
            self.mes_switch = False

        #弹出自定义框
        for item in node.getchildren():
            evt = ThreadDialogEvent(win_idx=self.win_idx, type='WORKSTAGE_MSGBOX', data={'win': self.win, 'item_attr': item.attrib})
            wx.PostEvent(self.win, evt)
            status, workstage_msgbox_value = self.data_queue.get()
            if status:
                self.dict.update(workstage_msgbox_value)
            else:
                return False
        return True

    def choose_workstage(self, product_xml):
        evt = ThreadDialogEvent(win_idx=self.win_idx, type='WORKSTAGE', data={'win': self.win, 'xml': product_xml})
        wx.PostEvent(self.win, evt)
        status, workstage_value = self.data_queue.get()
        return status, workstage_value

    def get_customer_sn_value(self):
        if self.bind_info is not None:
            if self.bind_info[3] is not None:
                customer_sn_value = self.bind_info[3]
            else:
                customer_sn_value = 'NOT FOUND'
        else:
            customer_sn_value = 'NOT FOUND'

        return customer_sn_value

    def run(self):
        try:
            result = PASS
            self.__keepgoing = True
            with THREAD_LOCK:
                prepare_status = self.prepare()

            if prepare_status:
                self.popupobj['isUsing'] = False
                self.popupobj[self.name].update({'win_idx':self.win_idx, 'first_run_by_hand': True, 'isRunning':True})
            else:
                self.postclose()
                self.popupobj['isUsing'] = False
                self.popupobj[self.name].update({'win_idx':self.win_idx , 'first_run_by_hand': False, 'isRunning': False })
                return

            start_time = datetime.now()
            wx.CallAfter(self.status_text.SetLabel, '')
            wx.CallAfter(self.name_text.SetLabel, u'{}-产品{}'.format(self.name, self.product_name) )
            self.section_message(u'正在测试产品：{}'.format(self.product_name))
            wx.CallAfter(self.sn_text.SetLabel, self.dict.get('@SN', '') )
            wx.CallAfter(self.dev_win.SetBackgroundColour, COLOUR_START)
            wx.CallAfter(self.dev_win.Refresh)
            for runorder, order in self.xml.get_seq():
                if runorder.get(self.xml._run) == 'True' and self.__keepgoing:
                    if ( runorder.attrib.has_key('station') and self.get_tag_value(runorder, 'station') == self.appconfig['station_name']) \
                            or  ( not runorder.attrib.has_key('station') ):
                        item_ret = self.item_test(order, runorder)
                        self.section_message(item_ret)
                        result = item_ret[1]
                        if result == FAIL: break

            end_time = datetime.now()
            diff_time = (end_time - start_time).seconds
            start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
            end_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
            self.section_message(u'总用时：{}s'.format(diff_time))
            self.close(start_time, end_time, diff_time, result)
        except etree.XMLSyntaxError as e:
            wx.CallAfter(self.status_text.SetLabel, ERROR)
            wx.CallAfter(self.dev_win.SetBackgroundColour, COLOUR_GRAY)
            self.popupobj[self.name].update({'first_run_by_hand': False})
            self.section_message(u'配置文件格式错误:{}\n错误信息:{}'.format(e.filename, e.message) , showcolor=True)
            self.logger.error(errorencode(traceback.format_exc()))
        except re.error  as e:
            wx.CallAfter(self.status_text.SetLabel, ERROR)
            wx.CallAfter(self.dev_win.SetBackgroundColour, COLOUR_GRAY)
            self.popupobj[self.name].update({'first_run_by_hand': False})
            self.section_message(u'正则表达式错误,错误信息({})!!!'.format(e.message), showcolor=True)
            self.logger.error(errorencode(traceback.format_exc()))
        except IOError as e:
            wx.CallAfter(self.status_text.SetLabel, ERROR)
            wx.CallAfter(self.dev_win.SetBackgroundColour, COLOUR_GRAY)
            self.popupobj[self.name].update({'first_run_by_hand': False})
            self.section_message(u'IOError: {}'.format(e.message), showcolor=True)
            self.logger.error(errorencode(traceback.format_exc()))
        except Exception as e:
            wx.CallAfter(self.status_text.SetLabel, ERROR)
            wx.CallAfter(self.dev_win.SetBackgroundColour, COLOUR_GRAY)
            self.popupobj[self.name].update({'first_run_by_hand': False})
            self.logger.error(unicode(traceback.format_exc(), errors='ignore', encoding='gbk'))
            self.section_message(u'脚本运行错误:{}'.format(errorencode(traceback.format_exc())) , showcolor=True)
        finally:
            self.postclose()

    def color_change_by_test_result(self, result):
        if result == PASS:
            wx.CallAfter(self.dev_win.SetBackgroundColour, COLOUR_PASS)
            wx.CallAfter(self.status_text.SetLabel, PASS)
        elif result==FAIL:
            self.popupobj[self.name].update({'first_run_by_hand': False})
            wx.CallAfter(self.dev_win.SetBackgroundColour, COLOUR_FAIL)
            wx.CallAfter(self.status_text.SetLabel, FAIL)

        wx.CallAfter(self.dev_win.Refresh)

    def write_record_to_database(self, start_time, end_time, diff_time, result, withmesfeature=True):
        operator =  self.appconfig['wn'] + '[{}]'.format(self.appconfig['wn_name'])
        sn = self.dict['@SN']
        mac = self.dict['@MAC']
        guid = ''
        logserial = self.log_area.GetValue()
        logprocess = self.section_log.GetValue()
        logserial = logserial.replace("\"", "\\\"")
        logprocess = logprocess.replace("\"", "\\\"")
        workstage = self.appconfig['station_name']
        if withmesfeature or self.appconfig['worktable_loaded']:
            product_name = self.mes_attr['extern_productname']
            product_type = self.mes_attr['extern_producttype']
            product_code = self.mes_attr['extern_productcode']
            product_version = self.mes_attr['extern_productversion']
            lotno = self.mes_attr['extern_lotno']
            bomcode = self.mes_attr['extern_bomcode']
            workorder = self.mes_attr.get('extern_WJTableName', '')
            subline = self.mes_attr.get('extern_SubLine', '')
            sql = "insert into sn_table(sn, result, starttime, endtime, totaltime, operator ,workorder, bomcode, productname, productver, lotno, guid, description, logserial, logprocess, segment1, segment2, segment3, segment4) " \
                  "values(\"{}\",\"{}\", \"{}\", \"{}\", \"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\",\"{}\", \"{}\", \"{}\", \"{}\",  \"{}\",  \"{}\") ".format(
                sn, result, start_time, end_time, str(diff_time), operator, workorder, bomcode, product_name, product_version, lotno, guid, 'remark', logserial, logprocess, mac, product_code, workstage, subline)

            # self.access_manager.insert_sn(sn, result, start_time, end_time, str(diff_time), operator, workorder, bomcode, product_name, product_version, lotno, guid, logserial, logprocess)
        else:
            sql = "insert into sn_table(sn, result, starttime, endtime, totaltime, operator, productname, guid, logserial, logprocess, segment1, segment3)" \
                  " values(\"{}\", \"{}\", \"{}\", \"{}\",\"{}\", \"{}\",\"{}\", \"{}\",\"{}\", \"{}\", \"{}\",  \"{}\" )".format(sn, result, start_time, end_time, str(diff_time), operator, self.product_name, guid, logserial, logprocess, mac, workstage)
            # self.access_manager.insert_sn(sn, result, start_time, end_time, str(diff_time), operator, '', '', self.product_name, '', '', guid, logserial, logprocess)
        try:
            self.log_cursor.execute(sql)
            self.log_conn.commit()
        except Exception as e:
            self.logger.error(errorencode(traceback.format_exc()))
            self.log_conn.rollback()

    def mes_write(self, result):
        ret = None
        if result == PASS:
            with THREAD_LOCK:
                dlg = wx.MessageDialog(self.win, u'选择OK，测试完毕；选择NG，输入不良代码', u'{}测试OK'.format(self.port) , style=wx.OK|wx.CANCEL|wx.CENTER)
                dlg.SetOKCancelLabels('OK', 'NG')
                if dlg.ShowModal() == wx.ID_OK:
                    ret = self.mes_write_ok(PASS)
                else:
                    ret = self.mes_write_ok(FAIL)
        else:
            ret = self.mes_write_ok(FAIL)
        return ret

    #unit test pass, write ok data to mes
    def mes_write_ok(self, result):
        repair_status, repair_msg = feature.mes_check_is_notin_repair(self.mes_attr)
        use_status, use_status_code, use_msg = feature.mes_check_is_in_current_procedurce(self.appconfig, self.mes_attr['extern_SN'])
        if not (repair_status and use_status):
            msg = repair_msg + use_msg + ',不能重复过站'
            self.section_message(msg, showcolor=True)
            return True

        extern_SerialNumber = self.mes_attr['extern_SerialNumber']
        extern_WJTableName = self.mes_attr['extern_WJTableName']
        extern_SubLineCode = self.mes_attr['extern_SubLineCode']
        extern_stritemmemo = self.mes_attr['extern_stritemmemo']
        extern_work_done_status = self.mes_attr['extern_work_done_status']
        extern_strWorkCode2 = self.mes_attr['extern_strWorkCode2']
        extern_strmpk = self.mes_attr['extern_strmpk']
        extern_CompSendno = self.mes_attr['extern_CompSendno']
        extern_stritemtype = self.mes_attr['extern_stritemtype']
        extern_stritemversion = self.mes_attr['extern_stritemversion']
        extern_SubTestPosition = self.mes_attr['extern_SubTestPosition']
        extern_AttempterCode = self.mes_attr['extern_AttempterCode']
        extern_SubID = self.mes_attr['extern_SubID']
        extern_Num1 = self.mes_attr['extern_Num1']
        extern_ScanType = self.mes_attr['extern_ScanType']
        extern_SubAttemperCode = self.mes_attr['extern_SubAttemperCode']
        extern_stritemcode = self.mes_attr['extern_stritemcode']
        extern_CompSendmpk = self.mes_attr['extern_CompSendmpk']
        extern_SubLine = self.mes_attr['extern_SubLine']
        op_workers = self.mes_attr['op_workers']
        strRepair = self.mes_attr['extern_repair']

        strBarCode = self.mes_attr['extern_SN']
        strCompSendno = extern_CompSendno
        strCompSendmpk = extern_CompSendmpk

        sql = "SELECT name FROM  DMSNEW.view_workclasstype where  to_number(to_char(sysdate,'HH24'))  >= to_number(substr(describe,1,2)) " + \
              " and to_number(to_char(sysdate,'HH24')) < to_number(substr(describe,7,2))"
        sql_value = self.mes_cursor.execute(sql).fetchall()
        classname = mes_value(sql_value[0][0])

        try:
            # write failed
            strbadposition = ''
            commonName = self.appconfig['wn'] + self.appconfig['wn_name'] + '[AutoTest]'
            strType = u'备注'

            if result == FAIL:
                with THREAD_LOCK:
                    evt = ThreadDialogEvent(win_idx=self.win_idx, type='BADCODE', data={})
                    wx.PostEvent(self.win, evt)
                    status, badvalue = self.data_queue.get()
                    if not status: return None
                    (strbadname, strbadtype, strType) = badvalue
                    self.data_queue.task_done()
                    repair_flag = 'yes'
            else:
                strbadname = strbadtype = strType = ''
                repair_flag = 'no'

            sql_station_out = "insert into " + "DMSNEW." + extern_WJTableName + "(subid,barcode,subattemper_code,line_code2,product_code,product_version,product_type,attempter_code,qulity_flag"
            sql_station_out  +=  ",qulity_plobolem,repair1,qualityposition,scan_position,mpk,produce_group,scan_person,aim_clint,testposition,describe,repair,segment2,sendno,sendmpk) values(" \
                                 + extern_SerialNumber + ",'" + strBarCode + "','" + extern_SubAttemperCode + "','" + extern_SubLine + "','" + extern_stritemcode + "','" + extern_stritemversion + "','" + \
                                 extern_stritemtype + "','" + extern_AttempterCode + "','" + repair_flag +"'" + ","
            sql_station_out += "'" + strbadname + "','" + strbadtype + "','" + strbadposition + "','L','" + extern_strmpk + "','" + classname + "','" + commonName + "','" \
                               + extern_strWorkCode2 + "','" + extern_SubTestPosition + "','" + strType + "','" + strRepair + "','" + extern_stritemmemo + "','" + strCompSendno + "','" + strCompSendmpk + "' ) "

            sql_station_in = "insert into " + "DMSNEW." + extern_WJTableName + \
                             "(subid, barcode, subattemper_code, line_code2 ,product_code,product_version,product_type,attempter_code,produce_group,mpk,scan_person, aim_clint, testposition,segment2,  sendno,sendmpk)  values(" \
                             + extern_SerialNumber + ",'" + strBarCode + "','" + extern_SubAttemperCode + "','" + extern_SubLineCode + "','" + \
                             extern_stritemcode + "','" + extern_stritemversion + "','" + extern_stritemtype + "','" + extern_AttempterCode + \
                             "','" + classname + "','" + extern_strmpk + "','" + commonName + "','" + extern_strWorkCode2 + "','" + \
                             extern_SubTestPosition + "','" + extern_stritemmemo + "','" + strCompSendno + "','" + strCompSendmpk + "' )"

            #step 1, 2
            self.mes_conn.commit()
            self.mes_cursor.execute(sql_station_in)
            self.mes_cursor.execute(sql_station_out)

            #step 3
            sql_update_main_barcode = " UPDATE  DMSNEW.WORK_MAIN_BARCODE  SET  NUMR=(numr+2), OUT_TIME=sysdate where  BARCODE='" + strBarCode + "'   "
            self.mes_cursor.execute(sql_update_main_barcode)

            sql = "select (select count(distinct(barcode)) from dmsnew.{worktable} where subattemper_code='{sub_attemper_table}'),  " \
                  "(select nvl(sum(decode(qulity_flag||scan_type||segment13,'no正常生产no',1,0)),0) from dmsnew.{worktable} b where " \
                  "(b.barcode,b.scan_time) in(select barcode,max(scan_time) from dmsnew.{worktable} where subattemper_code='{sub_attemper_table}' " \
                  "group by barcode ) and subattemper_code='{sub_attemper_table}' and qulity_flag='no' and scan_type='正常生产' and scan_position='L' " \
                  "and segment13='no' )  from dual".format(worktable=extern_WJTableName, sub_attemper_table=extern_SubAttemperCode)
            sql_value = self.mes_cursor.execute(sql).fetchone()
            if sql_value:
                strCount1, strCount2 = sql_value[0], sql_value[1]
                if strCount2 > strCount1:
                    strCount2 = strCount1

            #extern_Num1  安排加工数
            if (extern_Num1 <= strCount2):
                sql = "update DMSNEW.mtl_sub_attemper set state= '已完工',rea_begin_date=nvl(rea_begin_date,sysdate),rea_end_date=sysdate, " \
                      "LINE_HEAD_NUM=({0}), ine_last_num=({0}),TOTALSENDNUM ={1}  where sub_attempter_code='{2}' ".format(extern_Num1, op_workers, extern_SubAttemperCode)
                self.mes_cursor.execute(sql)
                if (extern_work_done_status == 0):
                    sql = "update DMSNEW.mtl_attemper set state='已完工',rea_begin_date=nvl(rea_begin_date,sysdate),real_finish_date=sysdate where attemper_code='" + extern_AttempterCode + "'"
                    self.mes_cursor.execute(sql)

                    sql = "update DMSNEW.work_workjob set  STATE='已完工',rea_first_date=nvl(rea_first_date,sysdate),rea_last_date=sysdate where  workjob_code='" + extern_WJTableName + "'"
                    self.mes_cursor.execute(sql)
            else:
                sql = "update DMSNEW.mtl_sub_attemper set STATE='已开工',rea_begin_date=nvl(rea_begin_date,sysdate),rea_end_date=null, " \
                      "LINE_HEAD_NUM=('{0}'), ine_last_num=('{1}'),TOTALSENDNUM={2}  where  sub_attempter_code='{3}'".format(strCount1, strCount2, op_workers, extern_SubAttemperCode)
                self.mes_cursor.execute(sql)

                sql = "update DMSNEW.mtl_attemper set state='已开工',rea_begin_date=nvl(rea_begin_date,sysdate),real_finish_date=null where attemper_code='" + extern_AttempterCode + "'"
                self.mes_cursor.execute(sql)

                sql = "update DMSNEW.work_workjob set  state='已开工',rea_first_date=nvl(rea_first_date,sysdate),rea_last_date=null where workjob_code='" + extern_WJTableName + "'"
                self.mes_cursor.execute(sql)
        except Exception as e:
            self.mes_conn.rollback()
            self.logger.error(errorencode(traceback.format_exc()) )
            return None
        else:
            self.mes_conn.commit()
            self.section_message('{}自动过站成功'.format(strBarCode), showcolor=True)
            return  False if repair_flag == 'yes' else True

    #find substr in s, and return it's position
    def find_pos(self, sub, s, slice):
        sub_count = slice.count(sub)
        if sub_count == 0: return [(0, 0)]
        pos_list, s_length = [], len(s)

        start_pos_list, start_pos = [], 0
        slice_count = s.count(slice)
        for i in range(slice_count):
            start_pos =  s.find(slice, start_pos, s_length)
            start_pos_list.append(start_pos)
            start_pos += len(slice)

        for start_pos in start_pos_list:
            for i in range(sub_count):
                start_pos = s.find(sub, start_pos, s_length)
                end_pos = start_pos + len(sub)
                pos_list.append((start_pos, end_pos))
                start_pos = end_pos
        return  pos_list

    #hightlight match string
    def highlight_match(self, match, cmd_content):
        try:
            if match == None: return
            style = wx.TextAttr('white', 'black')
            base_pos = self.log_area.GetValue().find(cmd_content)
            match_relative_pos = match.span(1)
            match_absolute_pos = (match_relative_pos[0] + base_pos, match_relative_pos[1] + base_pos)
            self.log_area.SetStyle(match_absolute_pos[0], match_absolute_pos[1], style)
        except Exception as e:
            self.logger.error(errorencode(traceback.format_exc()))

    #calculate total aging time
    def aging_total(self, cmd_content):
        time_list = re.findall('Test Time\s*:\s*(\d+)\s*s', cmd_content, re.I)
        totol_time = 0
        for time in time_list:
            totol_time += int(time)
        return totol_time/(3600.00)

    def time_delta(self, time_str):
        time_search = re.search(r'(?P<date>\d{4}-\d{2}-\d{2}).+(?P<time>\d{2}:\d{2}:\d{2})', time_str)
        d = time_search.groups()[0].split('-')
        t = time_search.groups()[1].split(':')
        d1, d2, d3 = int(d[0]), int(d[1]), int(d[2])
        t1, t2, t3 = int(t[0]), int(t[1]), int(t[2])
        device_date = datetime(d1, d2, d3, t1, t2, t3)
        device_time_sec = time.mktime(device_date.timetuple())
        return  time.mktime(time.localtime()) - device_time_sec

    def fan_regex(self, cmd, cmd_content, resultregex, item):
        ret = []

        which_re = self.get_tag_value(resultregex, 'which_re', '')
        which_value = self.get_tag_value(resultregex, 'which_value', '')
        level_re = self.get_tag_value(resultregex, 'level_re', '')
        speed_re = self.get_tag_value(resultregex, 'speed_re', '')
        level = self.get_tag_value(resultregex, 'level', '')
        level_range = self.get_tag_value(resultregex, 'level_range', '')
        extra_re = self.get_tag_value(resultregex, 'extra_re', '')
        extra_value = self.get_tag_value(resultregex, 'extra_value', '')

        which_re_match = re.search(which_re, cmd_content)
        level_re_match = re.search(level_re, cmd_content)
        speed_re_match = re.search(speed_re, cmd_content)
        extra_re_match = re.search(extra_re, cmd_content)

        self.highlight_match(which_re_match, cmd_content)
        self.highlight_match(level_re_match, cmd_content)
        self.highlight_match(speed_re_match, cmd_content)
        self.highlight_match(extra_re_match, cmd_content)

        try:
            which_re_match_value = which_re_match.groups()[0]
            level_re_match_value = level_re_match.groups()[0]
            speed_re_match_value = speed_re_match.groups()[0]
            extra_re_match_value = extra_re_match.groups()[0]

            if which_re_match_value in which_value.split('|'):
                ret.append(PASS)
            else:
                self.section_message(u'{}校验错误: 实为:{} 现为:{}'.format(which_re, [which_re_match_value], [which_value]), showcolor=True)
                ret.append(FAIL)

            if extra_re_match_value in extra_value.split("|"):
                ret.append(PASS)
            else:
                self.section_message(u'{}校验错误: 实为:{} 现为:{}'.format(extra_re, [extra_re_match_value], [extra_value]),showcolor=True)
                ret.append(FAIL)

            level_idx = level.split(',').index(level_re_match_value)

            level_range_value = level_range.split(',')[level_idx]
            level_range_value = level_range_value.split('-')

            #int(match2.groups()[0]) >= int(value_range[0]) and int(match2.groups()[0]) <= int(value_range[0])
            if int(speed_re_match_value) in xrange(int(level_range_value[0] ) , int(level_range_value[1]) + 1  ):
                ret.append(PASS)
            else:
                error_msg = '风扇实际速度：{} 不在 {}-{}范围，风扇级别{}.'.format(speed_re_match_value, level_range_value[0], level_range_value[1], level_re_match_value)
                self.section_message(error_msg, showcolor=True)
                ret.append(FAIL)
        except Exception as e:
            ret.append(FAIL)
            self.section_message(traceback.format_exc(), showcolor=True)
            self.logger.error(errorencode(traceback.format_exc()))
        finally:
            return FAIL if FAIL in ret else PASS

    #use regular express to verify the result
    def verify_result(self, cmd, cmd_content, item):
        result = []
        children = cmd.getchildren()
        agingtime = self.dict['@AGINGTIME']
        cmd_type = self.get_tag_value(cmd, 'cmdtype', 'cmd')

        #检测老化时间
        if self.get_tag_value(cmd, 'flag', None)== 'aging':
            aging_hour = self.aging_total(cmd_content)
            if aging_hour < agingtime:
                result.append(FAIL)
                self.section_message(u'FAIL：老化测试时间：{}H 老化设置时间：{:.2f}H'.format(round(aging_hour, 2), agingtime), True )
            else:
                result.append(PASS)
                self.section_message(u'PASS：老化测试时间：{}H 老化设置时间：{:.2f}H'.format(round(aging_hour, 2), agingtime))

        if len(children) == 0 or cmd_type not in ['cmd', 'fping', 'null']: return result;
        for resultregex  in children:
            assign_value = resultregex.attrib.get('assign', 'NULL')
            if resultregex.tag == 'fan':
                ret = self.fan_regex(cmd, cmd_content, resultregex, item)
                result.append(ret)
                self.dict[assign_value] = str(True) if ret == PASS else str(False)
                continue

            match_value = None
            regex = self.get_tag_value(resultregex, 'regex', None)
            errormsg = self.get_tag_value(resultregex, 'errormsg', None)
            regex_flag = self.get_tag_value(resultregex, 'flag',  '').split('|')
            match = re.search(regex, cmd_content)
            if match:
                match_value = match.groups()[0]
            else:
                self.section_message(u'未校验：{}'.format(regex), showcolor=True)
                result.append(FAIL)
                self.dict[assign_value] = str(False)
                continue

            self.highlight_match(match, cmd_content)
            match_value = feature.convert_value(match_value, regex_flag)
            if resultregex.attrib.has_key('assignto'):
                self.dict[resultregex.attrib.get('assignto')] = match_value
            #检测时间误差
            if 'time' in regex_flag:
                time_delta = self.time_delta(match_value)
                timedelta_permit = self.get_tag_value(resultregex, 'timedelta', '30')
                if int(timedelta_permit) <  abs(time_delta):
                    self.section_message(u'FAIL：测试时间误差:{}s  允许时间误差:{}s'.format(time_delta, timedelta_permit))
                    self.dict[assign_value] = str(False)
                    result.append(FAIL)
                else:
                    self.section_message(u'PASS：测试时间误差:{}s  允许时间误差:{}s'.format(time_delta, timedelta_permit))
                    self.dict[assign_value] = str(True)
                    result.append(PASS)

            if resultregex.attrib.has_key('value'):
                value = self.get_tag_value(resultregex, 'value',  '')
                value_list = value.split('|')
            elif resultregex.attrib.has_key('value_range'):
                value = self.get_tag_value(resultregex, 'value_range', '')
                value_min, value_max = value.split('-')
                if match_value.isdigit() and value_min.isdigit() and value_max.isdigit():
                    match_value, value_min, value_max = int(match_value), int(value_min), int(value_max)
                    value_list = xrange(value_min, value_max + 1)
                else:
                    value_list = None
            else:
                value_list = None

            if match:
                if value_list == None:
                    self.dict[assign_value] = str(True)
                    result.append(PASS)
                elif match_value in value_list:
                    self.dict[assign_value] = str(True)
                    result.append(PASS)
                elif 'not' in regex_flag:
                    if match_value not in value_list:
                        self.dict[assign_value] = str(True)
                        result.append(PASS)
                    else:
                        self.dict[assign_value] = str(False)
                        result.append(FAIL)
                else:
                    match_name = match.groupdict().keys()[0] if match.groupdict() else regex
                    if errormsg:
                        self.section_message(errormsg, True)
                    else:
                        self.section_message( u'{}校验错误: 实为:{} 现为:{}'.format(match_name, [match_value], [value]) , showcolor=True)
                    self.dict[assign_value] = str(False)
                    result.append(FAIL)
        return result

    def get_tag_value(self, tag, attr, default=''):
        attr_value =  tag.get(attr, default)
        if attr_value == None: return  None
        if '@' in attr_value:
            for key in  sorted( re.findall('(@\w+)', attr_value), key=len,  reverse=True ):
                value = self.dict[key]
                attr_value = attr_value.replace(key, value)

        if '$' in attr_value:
            for key in sorted(re.findall(r'(\$\w+)', attr_value), key=len, reverse=True):
                value = self.dict[key]
                attr_value = attr_value.replace(key, value)
        return attr_value

    def cmd_test(self, cmd, item, item_controller):
        now = datetime.now()
        self.dict['@YEAR'] = now.year
        self.dict['@MONTH'] = now.month
        self.dict['@DAY'] = now.day
        self.dict['@HOUR'] = now.hour
        self.dict['@MINUTE'] = now.minute
        self.dict['@SEC'] = now.second
        self.dict['@NOW'] = '{}{:0>2}{:0>2}{:0>2}{:0>2}{:0>2}'.format(now.year, now.month, now.day, now.hour, now.minute, now.second)
        self.dict['@NOW1'] = '{} {} {} {} {} {}'.format(now.hour, now.minute, now.second, now.year, now.month, now.day)

        result, cmd_content = PASS, ''
        cmd_endflag = self.get_tag_value(cmd, 'endflag', None)
        cmd_type = self.get_tag_value(cmd, 'cmdtype', 'cmd')
        cmd_retrytime = self.get_tag_value(cmd, 'retry', '0')
        cmd_flag = self.get_tag_value(cmd, 'flag', '')
        cmd_timeout = float( self.get_tag_value(cmd, 'timeout', '10') )
        cmd_delay = float(self.get_tag_value(cmd, 'delay', '0'))
        cmd_str =  self.get_tag_value(cmd, 'command', '')
        if cmd_type in ['cmd', 'multicmd']:
            default_errormsg = u'检查 命令:{} 超时时间:{} 结束标志:{}'.format(cmd_str, cmd_timeout, cmd_endflag)
        else:
            default_errormsg = None
        cmd_errormsg = self.get_tag_value(cmd, 'errormsg', default_errormsg)

        try:
            cmd_retrytime = int(cmd_retrytime)
            cmd_timeout = float(cmd_timeout)
        except ValueError as e:
            cmd_timeout, cmd_retrytime = 1 , 0

        if cmd_type in ['cmd', 'multicmd']:
            if cmd_type == 'multicmd':
                for child_cmd in cmd.getchildren():
                    cmd_str += self.get_tag_value(child_cmd, 'command', '') + self.linefeed

            cmd_result, cmd_content = self.cmd_run(locals())
            verify_result = self.verify_result(cmd, cmd_content, item)
            if cmd_result == FAIL or verify_result.__contains__(FAIL):
                while cmd_retrytime > 0:
                    cmd_retrytime -= 1
                    cmd_result, cmd_content = self.cmd_run(locals())
                    verify_result = self.verify_result(cmd, cmd_content, item)
                    if cmd_result == PASS and not verify_result.__contains__(FAIL): break

            if cmd_result == FAIL or verify_result.__contains__(FAIL):
                result = FAIL
                if cmd_errormsg:
                    self.section_message(cmd_errormsg, True)
        elif cmd_type == 'function':
            func = getattr(self, cmd_str)
            cmd_content, istimeout = func(cmd)
            if istimeout:
                if cmd_errormsg: self.section_message(cmd_errormsg, True)
                result = FAIL
        elif cmd_type == 'dialog':
            with THREAD_LOCK:
                dlg_style = self.get_tag_value(cmd, 'style', '').strip().lower()
                caption = self.get_tag_value(cmd, 'caption', 'Info')
                style = wx.OK if dlg_style == 'ok' else  wx.OK | wx.CANCEL
                dlg = wx.MessageDialog(None, cmd_str, '{}:{}'.format(self.name, caption), style=style)
                dlg.CentreOnParent()
                if dlg.ShowModal() == wx.ID_CANCEL: result = cmd_result = FAIL
        elif cmd_type == 'session':
            self.section_message(cmd_str)
        elif cmd_type == 'null':
            cmd_content = cmd_str
            verify_result = self.verify_result(cmd, cmd_content, item)
            if verify_result.__contains__(FAIL):
                result = FAIL
                if cmd_errormsg:
                    self.section_message(cmd_errormsg, True)
        elif cmd_type == 'msgbox':
            with THREAD_LOCK:
                cmd.attrib.update({'type': cmd_type})
                evt = ThreadDialogEvent(win_idx=self.win_idx, type='WORKSTAGE_MSGBOX', data={'win': self.win, 'item_attr': cmd.attrib})
                wx.PostEvent(self.win, evt)
                status, workstage_msgbox_value = self.data_queue.get()
                self.dict.update(workstage_msgbox_value)
        elif cmd_type == 'sleep':
            exec 'time.sleep({})'.format(cmd_str)
        elif cmd_type == 'condition':
            s_keys_all = pd.Series(self.dict.keys())
            s_keys_dollar = s_keys_all[s_keys_all.str.startswith('$')]
            s_keys_at = s_keys_all[s_keys_all.str.startswith('@')]
            s_keys_mix = s_keys_dollar.append(s_keys_at, ignore_index=True)
            s_keys_mix = s_keys_mix.sort_values(ascending=False)
            for key in s_keys_mix.values:
                key_pattern = key.replace('$', '\$') if key.startswith('$') else key
                cmd_str = re.sub(key_pattern, str(self.dict[key]), cmd_str)
            result = PASS if eval(cmd_str) else FAIL
        elif cmd_type == 'item':
            for item_controller_local, item_local in self.xml.get_seq():
                if item_controller_local.tag == cmd_str:
                    item_ret = self.item_test(item_local, item_controller_local)
                    self.section_message(item_ret)
                    result = item_ret[1]
                    break
        return result

    def cmd_run(self, others):
        cmd_content, result = '', PASS
        cmd_str = others.get('cmd_str')
        cmd_endflag = others.get('cmd_endflag')
        cmd_timeout = others.get('cmd_timeout')
        cmd_errormsg = others.get('cmd_errormsg')
        cmd_flag = others.get('cmd_flag')
        cmd_flag = cmd_flag.split('|')
        start_time = time.time()
        cmd_delay = others.get('cmd_delay')
        self.dev.set_read_timeout(0.2)

        if cmd_endflag is None:
            cmd_endflag_list = None
        else:
            cmd_endflag_list = [v.lower() for v in cmd_endflag.split('|') ]

        if 'hex' in cmd_flag:
            cmd_str = binascii.unhexlify(cmd_str)

        if 'detect' in cmd_flag:
            if 'char' in cmd_flag:
                for c_char in bytes(cmd_str):
                    time.sleep(cmd_delay)
                    self.write_cmd(bytes(c_char), extra={'endflag': cmd_endflag, 'timeout': cmd_timeout, 'flag': cmd_flag})
            else:
                self.write_cmd(bytes(cmd_str), extra={'endflag': cmd_endflag, 'timeout': cmd_timeout, 'flag': cmd_flag})
        else:
            if 'char' in cmd_flag:
                for c_char in bytes(cmd_str):
                    time.sleep(cmd_delay)
                    self.write_cmd(bytes(c_char), extra={'endflag': cmd_endflag, 'timeout': cmd_timeout, 'flag': cmd_flag})
                time.sleep(cmd_delay)
                self.write_cmd(bytes(self.linefeed), extra={'endflag': cmd_endflag, 'timeout': cmd_timeout, 'flag': cmd_flag})
            else:
                self.write_cmd(bytes(cmd_str + self.linefeed), extra={'endflag': cmd_endflag, 'timeout': cmd_timeout, 'flag': cmd_flag})

        while True:
            if time.time() - start_time > cmd_timeout:
                result = FAIL; break;

            if self.__keepgoing == False:
                result = FAIL; cmd_content += '<Process Stoped>'; break;
            line =  self.dev.read_line(fix=True)
            line = self.log_message(line)
            cmd_content += line
            if '--more--' in line.lower(): self.write_cmd(bytes(u' '))
            if cmd_endflag_list == None:
                result = PASS; break
            elif cmd_endflag_list:
                flag = False
                for cmd_endflag_part in cmd_endflag_list:
                    if cmd_endflag_part in line.lower():
                        result = PASS;flag=True; break
                if flag:break;
            elif line == '':
                continue
        return (result, cmd_content)

    def item_test(self, item, item_controller, record_flag=True):
        item_stage_text = self.get_tag_value(item_controller, 'cn', None)
        if not item_stage_text: item_stage_text = item_controller.tag
        self.status_text.SetLabel(u'正在测试：{}'.format(item_stage_text))
        if record_flag: self.recored_process(content=item_controller.tag, type="mode_in")
        #self.stage_text.SetLabelText(item_stage_text)
        start_time, result = datetime.now(), PASS
        for cmd in item.getchildren():
            if cmd.tag == 'cmd':
                if self.cmd_test(cmd, item, item_controller) == FAIL:
                    result = FAIL; break
            elif cmd.tag == 'if':
                if_judge_result = self.item_test(cmd, item_controller, False)[1]
                if_item_test_result = self.if_item_test(cmd, if_judge_result, item_controller)
                if if_item_test_result == FAIL:
                    result = FAIL; break
            elif cmd.tag == 'for':
                value_list = self.get_tag_value(cmd, 'value')
                assign_name = cmd.get('assign', '@FOR_NONE')
                for assign_value in value_list.split(','):
                    self.dict[assign_name] = assign_value
                    result = self.item_test(cmd, item_controller, False)[1]
                    if result == FAIL: break

        end_time = datetime.now()
        diff_time = (end_time - start_time).seconds
        start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
        if record_flag: self.recored_process(content=item_controller.tag, type="mode_out")
        return (item_stage_text, result, start_time, end_time, diff_time)

    def if_item_test(self, item, result, item_controller):
        for child in item.getchildren():
            if result == PASS and child.tag == 'ok':
                if_item_result = self.item_test(child, item_controller, False)[1]
            elif result == FAIL and child.tag == 'fail':
                if_item_result = self.item_test(child, item_controller, False)[1]
        return if_item_result


    def recored_process(self, content=None, type="unset"):
        if type == 'mode_in':
            self.process_handle.write(u'进入 {} 步骤\n'.format(content))
        elif type == "mode_out":
            self.process_handle.write(u'离开 {} 步骤\n'.format(content))
        elif type == "cmd":
            self.process_handle.write(u'发送命令:{}\t命令属性{}\n'.format([content[0] ], content[1]) )
        elif type == "echo":
            if content:
                self.process_handle.write(u'回显内容:{}\n'.format([content]))
        elif type == "unset":
            self.process_handle.write(u'type unset:{}\n'.format([content]))

    def write_cmd(self, cmd='', extra={}):
        self.dev.write(cmd)
        self.recored_process(content=(cmd, extra), type="cmd")
