import operator
from ui.mixin import XMLParser
from bitstring import BitArray
from communicate.communicate import SerialCommunicate

class CheckSum:
    @classmethod
    def send_checksum(cls, valid_data:BitArray):
        sum = 0
        for byte_int in valid_data.tobytes():
            sum += byte_int

        return BitArray( hex(sum%256) )

    @classmethod
    def recv_checksum(cls, valid_data:BitArray):
        sum = 0
        for byte_int in valid_data:
            sum += byte_int

        return BitArray(hex(sum))[-8:]


def send_command(dev: SerialCommunicate, xml: XMLParser, type_: str):
    ele = xml.root.find( '{}[@type="{}"]'.format(xml._send_path, type_) )
    frameheader = ele.get('header', xml.default_send_frameheader)
    funchar = ele.get('funchar')
    datalen = ele.get('len')
    data = ele.get('data')

    valid_data  = BitArray('{}, {}, {}, {}'.format(frameheader, funchar, datalen, data))
    checksum_data = operator.attrgetter(xml.send_checksum_func)(CheckSum)(valid_data)

    final_data = valid_data + checksum_data
    print('send_command>', [final_data.tobytes()], 'type', [type_])
    dev.write(final_data.tobytes())



