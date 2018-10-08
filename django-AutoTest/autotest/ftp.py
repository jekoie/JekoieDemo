
from urllib.parse import urlparse
from ftputil import FTPHost
from django.conf import settings

def get_ftp():
    ftp_path = getattr(settings, 'FTP_PATH', 'ftp://szgy-chenjie:szgy-chenjie@192.168.60.70/soft/测试文件')
    parsed = urlparse(ftp_path)
    ftp = FTPHost(parsed.hostname, parsed.username, parsed.password)
    ftp.chdir(parsed.path)

    return ftp

class RFTP:
    def __init__(self):
        ftp_path = getattr(settings, 'FTP_PATH', 'ftp://szgy-chenjie:szgy-chenjie@192.168.60.70/soft/测试文件')
        parsed = urlparse(ftp_path)
        self.hostname = parsed.hostname
        self.username = parsed.username
        self.password = parsed.password
        self.path = parsed.path
        self.ftp = None

    def get_ftp(self):
        if self.ftp is None:
            self.ftp = FTPHost(self.hostname, self.username, self.password)
            self.ftp.chdir(self.path)
        else:
            try:
                self.ftp.chdir(self.path)
            except Exception as e:
                self.ftp = FTPHost(self.hostname, self.username, self.password)
                self.ftp.chdir(self.path)
        return self.ftp

    def remove_file(self, name):
        try:
            self.ftp.remove(name)
        except Exception as e:
            self.ftp.rmdir(name)
