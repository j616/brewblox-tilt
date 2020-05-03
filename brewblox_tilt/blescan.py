import sys
import struct
import bluetooth._bluetooth as bluez


def returnnumberpacket(pkt):
    myInteger = 0
    multiple = 256
    for c in pkt:
        myInteger += c * multiple
        multiple = 1
    return myInteger


def returnstringpacket(pkt):
    myString = ""
    for c in pkt:
        myString += "%02x" % c
    return myString


def printpacket(pkt):
    for c in pkt:
        sys.stdout.write("%02x " % c)


def get_packed_bdaddr(bdaddr_string):
    packable_addr = []
    addr = bdaddr_string.split(":")
    addr.reverse()
    for b in addr:
        packable_addr.append(int(b, 16))
    return struct.pack("<BBBBBB", *packable_addr)


def packed_bdaddr_to_string(bdaddr_packed):
    return ":".join("%02x" % i for i in struct.unpack(
        "<BBBBBB", bdaddr_packed[::-1]))


def twosComp(num, len):
    return num - (1 << len)


def hci_enable_le_scan(sock):
    hci_toggle_le_scan(sock, 0x01)


def hci_disable_le_scan(sock):
    hci_toggle_le_scan(sock, 0x00)


def hci_toggle_le_scan(sock, enable):
    ogf_le_ctl = 0x08
    ocf_le_set_scan_enable = 0x000C

    cmd_pkt = struct.pack("<BB", enable, 0x00)
    bluez.hci_send_cmd(sock, ogf_le_ctl, ocf_le_set_scan_enable, cmd_pkt)


def parse_events(sock, loop_count=100):
    le_meta_event = 0x3e
    le_advertising_report = 0x02
    old_filter = sock.getsockopt(bluez.SOL_HCI, bluez.HCI_FILTER, 14)

    # perform a device inquiry on bluetooth device #0
    # The inquiry should last 8 * 1.28 = 10.24 seconds
    # before the inquiry is performed, bluez should flush its cache of
    # previously discovered devices
    flt = bluez.hci_filter_new()
    bluez.hci_filter_all_events(flt)
    bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
    sock.setsockopt(bluez.SOL_HCI, bluez.HCI_FILTER, flt)
    myFullList = []
    for i in range(0, loop_count):
        pkt = sock.recv(255)
        ptype, event, plen = struct.unpack("BBB", pkt[:3])
        if event == bluez.EVT_INQUIRY_RESULT_WITH_RSSI:
            i = 0
        elif event == bluez.EVT_NUM_COMP_PKTS:
            i = 0
        elif event == bluez.EVT_DISCONN_COMPLETE:
            i = 0
        elif event == le_meta_event:
            subevent = pkt[3]
            pkt = pkt[4:]
            if subevent == le_advertising_report:
                num_reports = pkt[0]
                pkt_offset = 0
                for i in range(0, num_reports):
                    txpower = twosComp(pkt[pkt_offset - 2], 8)
                    rssi = twosComp(pkt[pkt_offset - 1], 8)
                    data = {
                        "mac": packed_bdaddr_to_string(
                            pkt[pkt_offset + 3:pkt_offset + 9]),
                        "uuid": returnstringpacket(
                            pkt[pkt_offset - 22: pkt_offset - 6]),
                        "major": returnnumberpacket(
                            pkt[pkt_offset - 6: pkt_offset - 4]),
                        "minor": returnnumberpacket(
                            pkt[pkt_offset - 4: pkt_offset - 2]),
                        "txpower": txpower,
                        "rssi": rssi
                        }

                    myFullList.append(data)
    sock.setsockopt(bluez.SOL_HCI, bluez.HCI_FILTER, old_filter)
    return myFullList
