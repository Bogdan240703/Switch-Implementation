#!/usr/bin/python3
import sys
import struct
import wrapper
import threading
import time
from wrapper import recv_from_any_link, send_to_link, get_switch_mac, get_interface_name
own_bridge_ID =  -1
root_bridge_ID = -2
vlans = []
interfaces = []

# Constants
DST_MAC = b'\x01\x80\xc2\x00\x00\x00'  # BPDU multicast MAC
DSAP = 0x42
SSAP = 0x42
CONTROL = 0x03
PROTOCOL_ID = 0x0000
PROTOCOL_VERSION = 0x00
BPDU_TYPE = 0x00  # Configuration BPDU
BPDU_FLAGS = 0x00
LLC_LENGTH = 38  # LLC total length for this BPDU frame

# BPDU Configuration Parameters (Example Values)
root_bridge_priority = 32768
root_bridge_mac = b'\x00\x1c\x0e\x87\x78\x00'
root_path_cost = 0
bridge_priority = 32768
bridge_mac = b'\x00\x1c\x0e\x87\x85\x00'
port_id = 0x8004
message_age = 1
max_age = 20
hello_time = 2
forward_delay = 15

def create_bpdu_packet(root_bridge_id, sender_bridge_id, port_id):
    # Pack BPDU Configuration section (31 bytes)
    bpdu_config = struct.pack(
        '!B8sI8sHHHHH',
        BPDU_FLAGS,
        struct.pack('!H6s', root_bridge_id, get_switch_mac()),
        root_path_cost,
        struct.pack('!H6s', sender_bridge_id, get_switch_mac()),
        port_id,
        message_age,
        max_age,
        hello_time,
        forward_delay
    )

    # LLC Header (3 bytes)
    llc_header = struct.pack('!BBB', DSAP, SSAP, CONTROL)

    # Total BPDU Frame (LLC_LENGTH + LLC Header + BPDU Header + BPDU Config)
    bpdu_frame = (
        DST_MAC +                       # Destination MAC
        get_switch_mac() +               # Source MAC (Function get_switch_mac() should return sender's MAC)
        struct.pack('!H', LLC_LENGTH) +  # LLC Length
        llc_header +                     # LLC Header
        struct.pack('!HBB', PROTOCOL_ID, PROTOCOL_VERSION, BPDU_TYPE) +  # BPDU Header
        bpdu_config                      # BPDU Configuration
    )
    
    return bpdu_frame
def parse_ethernet_header(data):
    # Unpack the header fields from the byte array
    #dest_mac, src_mac, ethertype = struct.unpack('!6s6sH', data[:14])
    dest_mac = data[0:6]
    src_mac = data[6:12]
    
    # Extract ethertype. Under 802.1Q, this may be the bytes from the VLAN TAG
    ether_type = (data[12] << 8) + data[13]

    vlan_id = -1
    # Check for VLAN tag (0x8100 in network byte order is b'\x81\x00')
    if ether_type == 0x8200:
        vlan_tci = int.from_bytes(data[14:16], byteorder='big')
        vlan_id = vlan_tci & 0x0FFF  # extract the 12-bit VLAN ID
        ether_type = (data[16] << 8) + data[17]

    return dest_mac, src_mac, ether_type, vlan_id

def create_vlan_tag(vlan_id):
    # 0x8100 for the Ethertype for 802.1Q
    # vlan_id & 0x0FFF ensures that only the last 12 bits are used
    return struct.pack('!H', 0x8200) + struct.pack('!H', vlan_id & 0x0FFF)

def send_bdpu_every_sec():
    while True:
        # TODO Send BDPU every second if necessary
        print(own_bridge_ID)
        print(root_bridge_ID)
        if own_bridge_ID==root_bridge_ID:
            print("")
            print("")
            print("laaaaalalallalaa")
            print(" ")
            
            for i in interfaces:
                if vlans[i]==-1:
                    pachet=create_bpdu_packet(root_bridge_ID,own_bridge_ID,i)
                    send_to_link(i,52,pachet)
                    print(" ")
        time.sleep(1)
def is_mac_broadcast(mac):
    if mac=='\xFF\xFF\xFF\xFF\xFF\xFF':
        return True
    else:
        return False
def is_mac_multicast(mac):
    if mac=="01:80:c2:00:00:00":
        return True
    else:
        return False

def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]
    global interfaces
    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    print("# Starting switch with id {}".format(switch_id), flush=True)
    print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))

    
    cam={}
    # Printing interface names
    for i in interfaces:
        print(get_interface_name(i))
    numefisier="./configs/switch"+str(switch_id)+".cfg"
    with open(numefisier, 'r') as file:
        content = file.read()  
    lines=content.split("\n")
    n=len(interfaces)
    priority=int(lines[0])
    global vlans
    
    vlans=n*[0]
    for i in range(1,n+1):
        lineaux=lines[i].split(" ")
        print(lineaux)
        for j in range(0,n):
            if get_interface_name(j)==lineaux[0]:
                if lineaux[1]=='T':
                    vlans[j]=-1
                else:
                    vlans[j]=int(lineaux[1])
    print(vlans)
    #aici o sa fac initiliaziarile pt stp
    port_states=n*[-1]
    for i in range(0,n):
        if vlans[i]==-1:
            port_states[i]=0
        else:
            port_states[i]=1
    global own_bridge_ID
    global root_bridge_ID
    own_bridge_ID =  priority
    root_bridge_ID = own_bridge_ID
    global root_path_cost
    root_path_cost = 0
    root_port=-1
    if own_bridge_ID==root_bridge_ID:
        for i in range(0,n):
            if vlans[i]==-1:
                port_states[i]=1
    # Create and start a new thread that deals with sending BDPU
    t = threading.Thread(target=send_bdpu_every_sec)
    t.start()
    while True:
        # Note that data is of type bytes([...]).
        # b1 = bytes([72, 101, 108, 108, 111])  # "Hello"
        # b2 = bytes([32, 87, 111, 114, 108, 100])  # " World"
        # b3 = b1[0:2] + b[3:4].
        interface, data, length = recv_from_any_link()
        # asta inseamna ca daca portul este blocat nu ar trebui sa ma intereseze pachetul primit asa ca il arunc ca sa nu fac bucle
        if port_states[interface]==0:
            continue

        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)
        dest_mac_aux=dest_mac
        # Print the MAC src and MAC dst in human readable format
        dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac = ':'.join(f'{b:02x}' for b in src_mac)

        # Note. Adding a VLAN tag can be as easy as
        

        print(f'Destination MAC: {dest_mac}')
        print(f'Source MAC: {src_mac}')
        print(f'EtherType: {ethertype}')
        print(f'Interface: {interface}')
        print("Received frame of size {} on interface {}".format(length, interface), flush=True)

        # TODO: Implement forwarding with learning
        if src_mac not in cam:
            cam[src_mac]=interface
        are_vlan=0
        if vlans[interface]!=-1:
            are_vlan=1
        if is_mac_broadcast(dest_mac_aux)==True or dest_mac not in cam:
            #trb sa trimitem pe toate porturile in afara de cel pe care a venit
            if is_mac_multicast(dest_mac)==True:
                root_priority_pachet = struct.unpack('!H', data[22:24])[0]
                cost_to_root=struct.unpack('!I', data[30:34])[0]
                print("a ajuns bdlpul bai frate")
                print(root_priority_pachet)
                print("Cost to root:")
                print(cost_to_root)
                if root_priority_pachet< root_bridge_ID:
                    ok=0
                    if root_bridge_ID==own_bridge_ID:
                        ok=1
                    root_bridge_ID=root_priority_pachet
                    root_path_cost+=10
                    root_port=i
                    if ok==1:
                        #inseamna ca "am fost" root
                        for i in interfaces:
                            if vlans[i]==-1 and i !=root_port:
                                port_states[i]=0
                    if port_states[root_port]==0:
                        port_states[root_port]=1
                    new_bpdu_packet = (
                                    data[:30] +                          
                                    struct.pack('!I', root_path_cost) +  
                                    struct.pack('!H', own_bridge_ID ) +
                                    data[36:]                            
                                )
                    for i in interfaces:
                        if vlans[i]==-1:
                            send_to_link(i,52,new_bpdu_packet)       
            else:
                for i in interfaces:
                    if i!= interface:
                        if vlans[i] == -1:
                            if vlans[interface]==-1:
                                send_to_link(i,length,data)
                            else:
                                #de adaugat vlan tag        
                                tagged_frame = data[0:12] + create_vlan_tag(vlans[interface]) + data[12:]
                                send_to_link(i,length+4,tagged_frame)
                        else:
                            print("Lapu")
                            if vlans[interface]==-1:
                                #de scos vlan si de trimis doar daca vlanu scos e egal cu vlanu intefertei pe care trimit
                                print(vlan_id)
                                if vlan_id == vlans[i]:
                                    print("mere bai")
                                    send_to_link(i,length-4,data[0:12]+data[16:])
                            else:
                                if vlans[interface] == vlans[i]:
                                    send_to_link(i,length,data)
        else:
            interf_de_trimis=cam[dest_mac]
            if vlans[interf_de_trimis]==-1:
                if vlans[interface]==-1:
                    send_to_link(interf_de_trimis,length,data)
                else:
                    tagged_frame = data[0:12] + create_vlan_tag(vlans[interface]) + data[12:]
                    send_to_link(interf_de_trimis,length+4,tagged_frame)
            else:
                #aici inseamna ca trimit la host
                if vlans[interface]!=-1:
                    if vlans[interface] == vlans[interf_de_trimis]:
                        send_to_link(interf_de_trimis,length,data)
                else:
                    if vlan_id == vlans[interf_de_trimis]:
                        print("mere bai")
                        send_to_link(interf_de_trimis,length-4,data[0:12]+data[16:])
        # TODO: Implement VLAN support
        # TODO: Implement STP support
        
        # data is of type bytes.
        # send_to_link(i, length, data)

if __name__ == "__main__":
    main()
