from lxml import etree

#测试产品基类
class BaseProduct:
    def __init__(self, path:str):
        self.xmlpath = path
        self.xmltree = etree.parse(path)
        self.xmlroot = self.xmltree.getroot()

        self.connect_directive = self.xmlroot.find('//send[@type="connect"]')
        self.optional_directive = self.xmlroot.find('//send[@type="connect"]')
        self.next_directive = self.xmlroot.find('//send[@type="next"]')

