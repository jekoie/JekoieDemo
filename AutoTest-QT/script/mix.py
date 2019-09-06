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
    dev.write(final_data.tobytes())


def convert(item, bytedata: BitArray):
    convert_method = item.get(XMLParser.AConvert, 'int') #type:str
    if convert_method == 'int':
        return bytedata.int
    elif 'ad' in convert_method:
        *_, divisor, multiplier = convert_method.split(',')
        return (bytedata.uint/float(divisor))*float(multiplier)
    elif convert_method == 'uint':
        return bytedata.uint
    elif convert_method == 'hex':
        return bytedata.hex.upper()

def convert_value(frame_data, item):
    convert_value = ''
    if XMLParser.Abytepos in item.keys():
        bytedata = BitArray()
        bytepos = item.get(XMLParser.Abytepos)
        if ',' in bytepos or '-' in bytepos:
            for pos_str in bytepos.split(','):
                pos_str = pos_str.replace(' ', '')
                if '-' not in pos_str:
                    bytedata.append(frame_data[int(pos_str): int(pos_str) + 1])

                elif '-' in pos_str:
                    min_pos_str, max_pos_str = pos_str.split('-')
                    for pos in range(int(min_pos_str), int(max_pos_str) + 1):
                        bytedata.append(frame_data[pos:pos + 1])
        else:
            bytedata.append(frame_data[int(bytepos): int(bytepos) + 1])

        convert_value = convert(item, bytedata)
    elif XMLParser.Abitpos in item.keys():
        byte_pos, bit_pos = item.get(XMLParser.Abitpos).split(',')
        bytedata = BitArray('uint:8={}'.format(frame_data[int(byte_pos)]))
        bitdata = bytedata[int(bit_pos): int(bit_pos) + 1]
        convert_value = convert(item, bitdata)

    return convert_value


def value_compare(convert_value, item) -> bool:
    result = False
    TYPE = type(convert_value)
    if XMLParser.AValue in item.keys():
        value = item.get(XMLParser.AValue, '')

        if isinstance(convert_value, (int, float)):
            if ',' in value or '-' in value:
                for value_str in value.split(','):
                    value_str = value_str.replace(' ', '')
                    if '-' not in value_str:
                        if TYPE(value_str) == convert_value:
                            result = True
                            break
                    elif '-' in value_str:
                        min_str, max_str = value_str.split('-')
                        if TYPE(min_str) <= convert_value <= TYPE(max_str):
                            result = True
                            break
            else:
                if TYPE(value) == convert_value:
                    result = True
        elif isinstance(convert_value, (str) ):
            if TYPE(value) == convert_value:
                result = True

    return result

