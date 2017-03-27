"""
TCP/IP Protocol Stack

WARNING: before parsing the application layer over a TCP stream, you must 
first combine all the TCP frames into a stream. See utils.tcpip for some solutions.
"""

from construct import *
from construct.lib import *


#===============================================================================
# layer 2, Ethernet
#===============================================================================

MacAddress = ExprAdapter(Byte[6],
    encoder = lambda obj,ctx: [int(part, 16) for part in obj.split("-")],
    decoder = lambda obj,ctx: "-".join("%02x" % b for b in obj), )

ethernet_header = "ethernet_header" / Struct(
    "destination" / MacAddress,
    "source" / MacAddress,
    "type" / Enum(Int16ub,
        IPv4 = 0x0800,
        ARP = 0x0806,
        RARP = 0x8035,
        X25 = 0x0805,
        IPX = 0x8137,
        IPv6 = 0x86DD,
        default = Pass,
    ),
)

#===============================================================================
# layer 2, ARP
#===============================================================================

# HwAddress = IfThenElse(this.hardware_type == "ETHERNET",
#     MacAddressAdapter(Bytes(this.hwaddr_length)),
#     Bytes(this.hwaddr_length)
# )

HwAddress = Bytes(this.hwaddr_length)

# ProtoAddress = IfThenElse(this.protocol_type == "IP",
#     IpAddressAdapter(Bytes(this.protoaddr_length)),
#     Bytes(this.protoaddr_length)
# )

ProtoAddress = Bytes(this.protoaddr_length)

arp_header = "arp_header" / Struct(
    "hardware_type" / Enum(Int16ub,
        ETHERNET = 1,
        EXPERIMENTAL_ETHERNET = 2,
        ProNET_TOKEN_RING = 4,
        CHAOS = 5,
        IEEE802 = 6,
        ARCNET = 7,
        HYPERCHANNEL = 8,
        ULTRALINK = 13,
        FRAME_RELAY = 15,
        FIBRE_CHANNEL = 18,
        IEEE1394 = 24,
        HIPARP = 28,
        ISO7816_3 = 29,
        ARPSEC = 30,
        IPSEC_TUNNEL = 31,
        INFINIBAND = 32,
    ),
    "protocol_type" / Enum(Int16ub,
        IP = 0x0800,
    ),
    "hwaddr_length" / Int8ub,
    "protoaddr_length" / Int8ub,
    "opcode" / Enum(Int16ub,
        REQUEST = 1,
        REPLY = 2,
        REQUEST_REVERSE = 3,
        REPLY_REVERSE = 4,
        DRARP_REQUEST = 5,
        DRARP_REPLY = 6,
        DRARP_ERROR = 7,
        InARP_REQUEST = 8,
        InARP_REPLY = 9,
        ARP_NAK = 10
        
    ),
    "source_hwaddr" / HwAddress,
    "source_protoaddr" / ProtoAddress,
    "dest_hwaddr" / HwAddress,
    "dest_protoaddr" / ProtoAddress,
)

#===============================================================================
# layer 2, Message Transport Part 2 (SS7 protocol stack)
# (untested)
#===============================================================================

mtp2_header = "mtp2_header" / BitStruct(
    "flag1" / Octet,
    "bsn" / BitsInteger(7),
    "bib" / Bit,
    "fsn" / BitsInteger(7),
    "sib" / Bit,
    "length" / Octet,
    "service_info" / Octet,
    "signalling_info" / Octet,
    "crc" / BitsInteger(16),
    "flag2" / Octet,
)

#===============================================================================
# layer 3, IP v4
#===============================================================================

IpAddress = ExprAdapter(Byte[4],
    encoder = lambda obj,ctx: list(map(int, obj.split("."))),
    decoder = lambda obj,ctx: "{0}.{1}.{2}.{3}".format(*obj), )


def ProtocolEnum(code):
    return Enum(code,
        ICMP = 1,
        TCP = 6,
        UDP = 17,
    )

ipv4_header = "ip_header" / Struct(
    EmbeddedBitStruct(
        "version" / Const(Nibble, 4),
        "header_length" / ExprAdapter(Nibble, 
            decoder = lambda obj, ctx: obj * 4, 
            encoder = lambda obj, ctx: obj / 4
        ),
    ),
    "tos" / BitStruct(
        "precedence" / BitsInteger(3),
        "minimize_delay" / Flag,
        "high_throuput" / Flag,
        "high_reliability" / Flag,
        "minimize_cost" / Flag,
        Padding(1),
    ),
    "total_length" / Int16ub,
    "payload_length" / Computed(this.total_length - this.header_length),
    "identification" / Int16ub,
    EmbeddedBitStruct(
        "flags" / Struct(
            Padding(1),
            "dont_fragment" / Flag,
            "more_fragments" / Flag,
        ),
        "frame_offset" / BitsInteger(13),
    ),
    "ttl" / Int8ub,
    "protocol" / ProtocolEnum(Int8ub),
    "checksum" / Int16ub,
    "source" / IpAddress,
    "destination" / IpAddress,
    "options" / Bytes(this.header_length - 20),
)

#===============================================================================
# layer 3, IP v6
#===============================================================================
def ProtocolEnum(code):
    return Enum(code,
        ICMP = 1,
        TCP = 6,
        UDP = 17,
    )

Ipv6Address = ExprAdapter(Byte[16],
    encoder = lambda obj,ctx: [int(part, 16) for part in obj.split(":")],
    decoder = lambda obj,ctx: ":".join("%02x" % b for b in obj), )

ipv6_header = "ip_header" / Struct(
    EmbeddedBitStruct(
        "version" / OneOf(BitsInteger(4), [6]),
        "traffic_class" / BitsInteger(8),
        "flow_label" / BitsInteger(20),
    ),
    "payload_length" / Int16ub,
    "protocol" / ProtocolEnum(Int8ub),
    "hoplimit" / Int8ub,
    Alias("ttl", "hoplimit"),
    "source" / Ipv6Address,
    "destination" / Ipv6Address,
)

#===============================================================================
# layer 3
# Message Transport Part 3 (SS7 protocol stack)
# (untested)
#===============================================================================

mtp3_header = "mtp3_header" / BitStruct(
    "service_indicator" / Nibble,
    "subservice" / Nibble,
)

#===============================================================================
# layer 3
# Internet Control Message Protocol for IPv4
#===============================================================================

echo_payload = "echo_payload" / Struct(
    "identifier" / Int16ub,
    "sequence" / Int16ub,
    "data" / Bytes(32),
    # length is implementation dependent, is anyone using more than 32 bytes?
)

dest_unreachable_payload = "dest_unreachable_payload" / Struct(
    Padding(2),
    "next_hop_mtu" / Int16ub,
    "host" / IpAddress,
    "echo" / Bytes(8),
)

dest_unreachable_code = "code" / Enum(Byte,
    Network_unreachable_error = 0,
    Host_unreachable_error = 1,
    Protocol_unreachable_error = 2,
    Port_unreachable_error = 3,
    The_datagram_is_too_big = 4,
    Source_route_failed_error = 5,
    Destination_network_unknown_error = 6,
    Destination_host_unknown_error = 7,
    Source_host_isolated_error = 8,
    Desination_administratively_prohibited = 9,
    Host_administratively_prohibited2 = 10,
    Network_TOS_unreachable = 11,
    Host_TOS_unreachable = 12,
)

icmp_header = "icmp_header" / Struct(
    "type" / Enum(Byte,
        Echo_reply = 0,
        Destination_unreachable = 3,
        Source_quench = 4,
        Redirect = 5,
        Alternate_host_address = 6,
        Echo_request = 8,
        Router_advertisement = 9,
        Router_solicitation = 10,
        Time_exceeded = 11,
        Parameter_problem = 12,
        Timestamp_request = 13,
        Timestamp_reply = 14,
        Information_request = 15,
        Information_reply = 16,
        Address_mask_request = 17,
        Address_mask_reply = 18,
        default = Pass,
    ),
    "code" / Switch(this.type, 
        {
            "Destination_unreachable" : dest_unreachable_code,
        },
        default = Byte
    ),
    "crc" / Int16ub,
    "payload" / Switch(this.type, 
        {
            "Echo_reply" : echo_payload,
            "Echo_request" : echo_payload,
            "Destination_unreachable" : dest_unreachable_payload,
        }, 
        default = Pass
    )
)

#===============================================================================
# layer 3
# Internet Group Management Protocol, Version 2
#
# http://www.ietf.org/rfc/rfc2236.txt
# jesse@housejunkie.ca
#===============================================================================

igmp_type = "igmp_type" / Enum(Byte, 
    MEMBERSHIP_QUERY = 0x11,
    MEMBERSHIP_REPORT_V1 = 0x12,
    MEMBERSHIP_REPORT_V2 = 0x16,
    LEAVE_GROUP = 0x17,
)

igmpv2_header = "igmpv2_header" / Struct(
    igmp_type,
    "max_resp_time" / Byte,
    "checksum" / Int16ub,
    "group_address" / IpAddress,
)

#===============================================================================
# layer 4
# Dynamic Host Configuration Protocol for IPv4
#
# http://www.networksorcery.com/enp/protocol/dhcp.htm
# http://www.networksorcery.com/enp/protocol/bootp/options.htm
#===============================================================================

dhcp4_option = "dhcp_option" / Struct(
    "code" / Enum(Byte,
        Pad = 0,
        Subnet_Mask = 1,
        Time_Offset = 2,
        Router = 3,
        Time_Server = 4,
        Name_Server = 5,
        Domain_Name_Server = 6,
        Log_Server = 7,
        Quote_Server = 8,
        LPR_Server = 9,
        Impress_Server = 10,
        Resource_Location_Server = 11,
        Host_Name = 12,
        Boot_File_Size = 13,
        Merit_Dump_File = 14,
        Domain_Name = 15,
        Swap_Server = 16,
        Root_Path = 17,
        Extensions_Path = 18,
        IP_Forwarding_enabledisable = 19,
        Nonlocal_Source_Routing_enabledisable = 20,
        Policy_Filter = 21,
        Maximum_Datagram_Reassembly_Size = 22,
        Default_IP_TTL = 23,
        Path_MTU_Aging_Timeout = 24,
        Path_MTU_Plateau_Table = 25,
        Interface_MTU = 26,
        All_Subnets_are_Local = 27,
        Broadcast_Address = 28,
        Perform_Mask_Discovery = 29,
        Mask_supplier = 30,
        Perform_router_discovery = 31,
        Router_solicitation_address = 32,
        Static_routing_table = 33,
        Trailer_encapsulation = 34,
        ARP_cache_timeout = 35,
        Ethernet_encapsulation = 36,
        Default_TCP_TTL = 37,
        TCP_keepalive_interval = 38,
        TCP_keepalive_garbage = 39,
        Network_Information_Service_domain = 40,
        Network_Information_Servers = 41,
        NTP_servers = 42,
        Vendor_specific_information = 43,
        NetBIOS_over_TCPIP_name_server = 44,
        NetBIOS_over_TCPIP_Datagram_Distribution_Server = 45,
        NetBIOS_over_TCPIP_Node_Type = 46,
        NetBIOS_over_TCPIP_Scope = 47,
        X_Window_System_Font_Server = 48,
        X_Window_System_Display_Manager = 49,
        Requested_IP_Address = 50,
        IP_address_lease_time = 51,
        Option_overload = 52,
        DHCP_message_type = 53,
        Server_identifier = 54,
        Parameter_request_list = 55,
        Message = 56,
        Maximum_DHCP_message_size = 57,
        Renew_time_value = 58,
        Rebinding_time_value = 59,
        Class_identifier = 60,
        Client_identifier = 61,
        NetWareIP_Domain_Name = 62,
        NetWareIP_information = 63,
        Network_Information_Service_Domain = 64,
        Network_Information_Service_Servers = 65,
        TFTP_server_name = 66,
        Bootfile_name = 67,
        Mobile_IP_Home_Agent = 68,
        Simple_Mail_Transport_Protocol_Server = 69,
        Post_Office_Protocol_Server = 70,
        Network_News_Transport_Protocol_Server = 71,
        Default_World_Wide_Web_Server = 72,
        Default_Finger_Server = 73,
        Default_Internet_Relay_Chat_Server = 74,
        StreetTalk_Server = 75,
        StreetTalk_Directory_Assistance_Server = 76,
        User_Class_Information = 77,
        SLP_Directory_Agent = 78,
        SLP_Service_Scope = 79,
        Rapid_Commit = 80,
        Fully_Qualified_Domain_Name = 81,
        Relay_Agent_Information = 82,
        Internet_Storage_Name_Service = 83,
        NDS_servers = 85,
        NDS_tree_name = 86,
        NDS_context = 87,
        BCMCS_Controller_Domain_Name_list = 88,
        BCMCS_Controller_IPv4_address_list = 89,
        Authentication = 90,
        Client_last_transaction_time = 91,
        Associated_ip = 92,
        Client_System_Architecture_Type = 93,
        Client_Network_Interface_Identifier = 94,
        Lightweight_Directory_Access_Protocol = 95,
        Client_Machine_Identifier = 97,
        Open_Group_User_Authentication = 98,
        Autonomous_System_Number = 109,
        NetInfo_Parent_Server_Address = 112,
        NetInfo_Parent_Server_Tag = 113,
        URL = 114,
        Auto_Configure = 116,
        Name_Service_Search = 117,
        Subnet_Selection = 118,
        DNS_domain_search_list = 119,
        SIP_Servers_DHCP_Option = 120,
        Classless_Static_Route_Option = 121,
        CableLabs_Client_Configuration = 122,
        GeoConf = 123,
    ),
    "value" / If(this.code != "Pad", Prefixed(Byte, GreedyBytes)),
)

dhcp4_header = "dhcp_header" / Struct(
    "opcode" / Enum(Byte,
        BootRequest = 1,
        BootReply = 2,
    ),
    "hardware_type" / Enum(Byte,
        Ethernet = 1,
        Experimental_Ethernet = 2,
        ProNET_Token_Ring = 4,
        Chaos = 5,
        IEEE_802 = 6,
        ARCNET = 7,
        Hyperchannel = 8,
        Lanstar = 9,
    ),
    "hardware_address_length" / Byte,
    "hop_count" / Byte,
    "transaction_id" / Int32ub,
    "elapsed_time" / Int16ub,
    "flags" / BitStruct(
        "broadcast" / Flag,
        Padding(15),
    ),
    "client_addr" / IpAddress,
    "your_addr" / IpAddress,
    "server_addr" / IpAddress,
    "relay_addr" / IpAddress,
    "client_hardware_addr" / Hex(Bytes(16)),
    "server_host_name" / Hex(Bytes(64)),
    "boot_filename" / Hex(Bytes(128)),
    # BOOTP/DHCP options
    # "The first four bytes contain the (decimal) values 99, 130, 83 and 99"
    "signature" / Const(b"\x63\x82\x53\x63"),
    "options" / GreedyRange(dhcp4_option),
)

#===============================================================================
# layer 4
# Dynamic Host Configuration Protocol for IPv6
#
# http://www.networksorcery.com/enp/rfc/rfc3315.txt
#===============================================================================

dhcp6_option = "dhcp_option" / Struct(
    "code" / Enum(Int16ub,
        OPTION_CLIENTID = 1,
        OPTION_SERVERID = 2,
        OPTION_IA_NA = 3,
        OPTION_IA_TA = 4,
        OPTION_IAADDR = 5,
        OPTION_ORO = 6,
        OPTION_PREFERENCE = 7,
        OPTION_ELAPSED_TIME = 8,
        OPTION_RELAY_MSG = 9,
        OPTION_AUTH = 11,
        OPTION_UNICAST = 12,
        OPTION_STATUS_CODE = 13,
        OPTION_RAPID_COMMIT = 14,
        OPTION_USER_CLASS = 15,
        OPTION_VENDOR_CLASS = 16,
        OPTION_VENDOR_OPTS = 17,
        OPTION_INTERFACE_ID = 18,
        OPTION_RECONF_MSG = 19,
        OPTION_RECONF_ACCEPT = 20,
        SIP_SERVERS_DOMAIN_NAME_LIST = 21,
        SIP_SERVERS_IPV6_ADDRESS_LIST = 22,
        DNS_RECURSIVE_NAME_SERVER = 23,
        DOMAIN_SEARCH_LIST = 24,
        OPTION_IA_PD = 25,
        OPTION_IAPREFIX = 26,
        OPTION_NIS_SERVERS = 27,
        OPTION_NISP_SERVERS = 28,
        OPTION_NIS_DOMAIN_NAME = 29,
        OPTION_NISP_DOMAIN_NAME = 30,
        SNTP_SERVER_LIST = 31,
        INFORMATION_REFRESH_TIME = 32,
        BCMCS_CONTROLLER_DOMAIN_NAME_LIST = 33,
        BCMCS_CONTROLLER_IPV6_ADDRESS_LIST = 34,
        OPTION_GEOCONF_CIVIC = 36,
        OPTION_REMOTE_ID = 37,
        RELAY_AGENT_SUBSCRIBER_ID = 38,
        OPTION_CLIENT_FQDN = 39,        
    ),
    "data" / Prefixed(Int16ub, GreedyBytes),
)

client_message = "client_message" / BitStruct(
    "transaction_id" / BitsInteger(24),
)

relay_message = "relay_message" / Struct(
    "hop_count" / Byte,
    "linkaddr" / Ipv6Address,
    "peeraddr" / Ipv6Address,
)

dhcp6_message = "dhcp_message" / Struct(
    "msgtype" / Enum(Byte,
        # these are client-server messages
        SOLICIT = 1,
        ADVERTISE = 2,
        REQUEST = 3,
        CONFIRM = 4,
        RENEW = 5,
        REBIND = 6,
        REPLY = 7,
        RELEASE_ = 8,
        DECLINE_ = 9,
        RECONFIGURE = 10,
        INFORMATION_REQUEST = 11,
        # these two are relay messages
        RELAY_FORW = 12,
        RELAY_REPL = 13,
    ),
    # relay messages have a different structure from client-server messages
    "params" / Switch(this.msgtype,
        {
            "RELAY_FORW" : relay_message,
            "RELAY_REPL" : relay_message,
        },
        default = client_message,
    ),
    "options" / GreedyRange(dhcp6_option),
)

#===============================================================================
# layer 4
# ISDN User Part (SS7 protocol stack)
#===============================================================================

isup_header = "isup_header" / Struct(
    "routing_label" / Bytes(5),
    "cic" / Int16ub,
    "message_type" / Int8ub,
    # mandatory fixed parameters
    # mandatory variable parameters
    # optional parameters
)

#===============================================================================
# layer 4
# Transmission Control Protocol (TCP/IP protocol stack)
#===============================================================================

tcp_header = "tcp_header" / Struct(
    "source" / Int16ub,
    "destination" / Int16ub,
    "seq" / Int32ub,
    "ack" / Int32ub,
    EmbeddedBitStruct(
        "header_length" / ExprAdapter(Nibble, 
            encoder = lambda obj, ctx: obj / 4,
            decoder = lambda obj, ctx: obj * 4,
        ),
        Padding(3),
        "flags" / Struct(
            "ns"  / Flag,
            "cwr" / Flag,
            "ece" / Flag,
            "urg" / Flag,
            "ack" / Flag,
            "psh" / Flag,
            "rst" / Flag,
            "syn" / Flag,
            "fin" / Flag,
        ),
    ),
    "window" / Int16ub,
    "checksum" / Int16ub,
    "urgent" / Int16ub,
    "options" / Bytes(this.header_length - 20),
)


#===============================================================================
# layer 4
# User Datagram Protocol (TCP/IP protocol stack)
#===============================================================================

udp_header = "udp_header" / Struct(
    "header_length" / Computed(lambda ctx: 8),
    "source" / Int16ub,
    "destination" / Int16ub,
    "payload_length" / ExprAdapter(Int16ub, 
        encoder = lambda obj, ctx: obj + 8,
        decoder = lambda obj, ctx: obj - 8,
    ),
    "checksum" / Int16ub,
)

#===============================================================================
# layer 4
# Domain Name System (TCP/IP protocol stack)
#===============================================================================

class DnsStringAdapter(Adapter):
    def _decode(self, obj, context):
        return ".".join(obj[:-1])
    def _encode(self, obj, context):
        return obj.split(".") + [""]

class DnsNamesAdapter(Adapter):
    def _decode(self, obj, context):
        return [x.label if x.islabel else x.pointer & 0x3fff for x in obj]
    def _encode(self, obj, context):
        return [dict(ispointer=1,pointer=x|0xc000) if isinstance(x,int) else dict(islabel=1,label=x) for x in obj]

dns_record_class = "class" / Enum(Int16ub,
    RESERVED = 0,
    INTERNET = 1,
    CHAOS = 3,
    HESIOD = 4,
    NONE = 254,
    ANY = 255,
)

dns_record_type = "type" / Enum(Int16ub,
    IPv4 = 1,
    AUTHORITIVE_NAME_SERVER = 2,
    CANONICAL_NAME = 5,
    NULL = 10,
    MAIL_EXCHANGE = 15,
    TEXT = 16,
    X25 = 19,
    ISDN = 20,
    IPv6 = 28,
    UNSPECIFIED = 103,
    ALL = 255,
)

query_record = "query_record" / Struct(
    "name" / DnsStringAdapter(RepeatUntil(len_(obj_)==0, PascalString(Byte, encoding="ascii"))),
    dns_record_type,
    dns_record_class,
)

labelpointer = Struct(
    "firstbyte" / Peek(Byte),
    "islabel" / Computed(this.firstbyte & 0b11000000 == 0),
    "ispointer" / Computed(this.firstbyte & 0b11000000 == 0b11000000),
    "label" / If(this.islabel, PascalString(Byte, encoding="ascii")),
    "pointer" / If(this.ispointer, Int16ub),
)

resource_record = "resource_record" / Struct(
    # http://www.zytrax.com/books/dns/ch15/#qname
    "names" / DnsNamesAdapter(RepeatUntil(obj_.ispointer or len_(obj_.label)==0, labelpointer)),
    dns_record_type,
    dns_record_class,
    "ttl" / Int32ub,
    "rdata" / Hex(Prefixed(Int16ub, GreedyBytes)),
)

dns = "dns" / Struct(
    "id" / Int16ub,
    "flags" / BitStruct(
        "type" / Enum(Bit,
            QUERY = 0,
            RESPONSE = 1,
        ),
        "opcode" / Enum(Nibble,
            STANDARD_QUERY = 0,
            INVERSE_QUERY = 1,
            SERVER_STATUS_REQUEST = 2,
            NOTIFY = 4,
            UPDATE = 5,
        ),
        "authoritive_answer" / Flag,
        "truncation" / Flag,
        "recursion_desired" / Flag,
        "recursion_available" / Flag,
        Padding(1),
        "authenticated_data" / Flag,
        "checking_disabled" / Flag,
        "response_code" / Enum(Nibble,
            SUCCESS = 0,
            FORMAT_ERROR = 1,
            SERVER_FAILURE = 2,
            NAME_DOES_NOT_EXIST = 3,
            NOT_IMPLEMENTED = 4,
            REFUSED = 5,
            NAME_SHOULD_NOT_EXIST = 6,
            RR_SHOULD_NOT_EXIST = 7,
            RR_SHOULD_EXIST = 8,
            NOT_AUTHORITIVE = 9,
            NOT_ZONE = 10,
        ),
    ),
    "question_count" / Rebuild(Int16ub, len_(this.questions)),
    "answer_count" / Rebuild(Int16ub, len_(this.answers)),
    "authority_count" / Rebuild(Int16ub, len_(this.authorities)),
    "additional_count" / Rebuild(Int16ub, len_(this.additionals)),
    "questions" / Array(this.question_count, query_record),
    "answers" / Array(this.answer_count, resource_record),
    "authorities" / Array(this.authority_count, resource_record),
    "additionals" / Array(this.additional_count, resource_record),
)

#===============================================================================
# entire IP stack
#===============================================================================

layer4_tcp = "layer4_tcp" / Struct(
    "header" / tcp_header,
    "next" / HexDump(Bytes(this._.header.payload_length - this.header.header_length)),
)

layer4_udp = "layer4_udp" / Struct(
    "header" / udp_header,
    "next" / HexDump(Bytes(this.header.payload_length)),
)

layer3_payload = "next" / Switch(this.header.protocol,
    {
        "TCP" : layer4_tcp,
        "UDP" : layer4_udp,
    },
    default = Pass
)

layer3_ipv4 = "layer3_ipv4" / Struct(
    "header" / ipv4_header,
    layer3_payload,
)

layer3_ipv6 = "layer3_ipv6" / Struct(
    "header" / ipv6_header,
    layer3_payload,
)

layer2_ethernet = "layer2_ethernet" / Struct(
    "header" / ethernet_header,
    "next" / Switch(this.header.type,
        {
            "IPv4" : layer3_ipv4,
            "IPv6" : layer3_ipv6,
        },
        default = Pass,
    ),
)

ip_stack = "ip_stack" / layer2_ethernet


