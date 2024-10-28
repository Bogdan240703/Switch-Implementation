#!/usr/bin/python3
# Savu Bogdan - 332CB
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
priority=-1
root_port=-1

dst_mac = b'\x01\x80\xc2\x00\x00\x00'  # multicast
dsap = 0x42
ssap = 0x42
control = 0x03
protocol_id = 0x0000
protocol_version = 0x00
bpdu_type = 0x00 
bpdu_flags = 0x00
llc_length = 38  

root_path_cost = 0
message_age = 0
max_age =0
hello_time = 0
forward_delay = 0

def create_bpdu_packet(root_bridge_id, sender_bridge_id, port_id):
    bpdu_config = struct.pack(
        '!B8sI8sHHHHH',
        bpdu_flags,
        struct.pack('!H6s', root_bridge_id, get_switch_mac()),
        root_path_cost,
        struct.pack('!H6s', sender_bridge_id, get_switch_mac()),
        port_id,
        message_age,
        max_age,
        hello_time,
        forward_delay
    )

    llc_header = struct.pack('!BBB', dsap, ssap, control)

    bpdu_frame = (
        dst_mac +                       
        get_switch_mac() +               
        struct.pack('!H', llc_length) +  
        llc_header +                     
        struct.pack('!HBB', protocol_id, protocol_version, bpdu_type) +  
        bpdu_config                      
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

        if own_bridge_ID==root_bridge_ID:      
            for i in interfaces:
                if vlans[i]==-1:
                    pachet=create_bpdu_packet(root_bridge_ID,own_bridge_ID,i)
                    send_to_link(i,52,pachet)
        time.sleep(1)
def is_mac_broadcast(mac):
    if mac=='ff:ff:ff:ff:ff:ff':
        return True
    else:
        return False
def is_mac_multicast(mac):
    if mac=="01:80:c2:00:00:00":
        return True
    else:
        return False
def citeste_configuratii_vlan(switch_id,n):
    global priority
    # deschid fisierul si ii parsez continutul
    numefisier="./configs/switch"+str(switch_id)+".cfg"
    with open(numefisier, 'r') as file:
        fisier = file.read()  
    text =  fisier.split("\n")
    
    priority=int(text[0])
    global vlans
    
    vlans=n*[0]
    for i in range(1,n+1):
        textaux=text[i].split(" ")
        for j in range(0,n):
            # aici fac ecvhivalenta intre denumirea portului din fisier si 
            # numarul interfetei cu care lucram in cod
            if get_interface_name(j)==textaux[0]:
                if textaux[1]=='T':
                    vlans[j]=-1
                else:
                    vlans[j]=int(textaux[1])
def prelucreaza_pachet_bpdu(interface,port_states,data):
    global priority
    global own_bridge_ID
    global root_bridge_ID
    global root_path_cost
    global root_port
    # imi extrag informatiile necesare din pachetul primit
    root_priority_pachet = struct.unpack('!H', data[22:24])[0]
    cost_to_root=struct.unpack('!I', data[30:34])[0]
    sender_bridge_id=struct.unpack('!H',data[34:36])[0]
    # aici tratez cazurile posibile pt atunci cand primesc un pachet bpdu
    # dupa modelul prezentat in enuntul temei de pe ocw
    if root_priority_pachet< root_bridge_ID:
        ok=0
        if root_bridge_ID==own_bridge_ID:
            ok=1
        root_bridge_ID=root_priority_pachet
        root_path_cost+=10
        root_port=interface
        if ok==1:
            #inseamna ca "am fost" root
            for i in interfaces:
                if vlans[i]==-1 and i !=root_port:
                    port_states[i]=0
        if port_states[root_port]==0:
            port_states[root_port]=1
        data_aux = (
                        data[:30] +                          
                        struct.pack('!I', root_path_cost) +  
                        struct.pack('!H', own_bridge_ID ) +
                        data[36:]                            
                    )
        for i in interfaces:
            if vlans[i]==-1 and i!=interface:
                send_to_link(i,52,data_aux) 
    elif root_priority_pachet==root_bridge_ID:
        if interface == root_port and cost_to_root+10<root_path_cost:
            root_path_cost=cost_to_root+10
        elif interface!=root_port:
            if cost_to_root>root_path_cost:   
                port_states[interface]=1   
    elif own_bridge_ID==sender_bridge_id:
        port_states[interface]=0
    if own_bridge_ID==root_bridge_ID:
        for i in interfaces:
                if vlans[i]==-1:
                    port_states[i]=1
def forward_broadcast(interface,port_states,length,data,vlan_id):
    for i in interfaces:
        # trimit pe toate interfete diferite de cea pe care am primit
        if i!= interface:
            if vlans[i] == -1:
                if vlans[interface]==-1 and port_states[i]==1:
                    # aici inseamna ca trimit pe port trunk si am primit pe port trunk
                    # deci are deja header-ul cu vlan id si fac forward direct
                    send_to_link(i,length,data)
                else:
                    # aici am de adaugat vlan tag pt ca inseamna ca am primit pachetul de pe un port access    
                    tagged_frame = data[0:12] + create_vlan_tag(vlans[interface]) + data[12:]
                    if port_states[i]==1: #trimit doar daca e portul deschis
                        send_to_link(i,length+4,tagged_frame)
            else:
                # aici inseamna ac trimit pe port access si deci trebuie sa scot header-ul 802.1Q
                if vlans[interface]==-1:
                    # inseamna ca a venit de pe un port trunk si are header
                    # scot vlan si trimit doar daca vlanul din header e egal cu vlanul intefertei pe care trimit
                    if vlan_id == vlans[i] and port_states[i]==1:
                        send_to_link(i,length-4,data[0:12]+data[16:])
                else:
                    # inseamna ca a venit de la un host si nu are header deci nu mai scot nimic,
                    # dar trimit doar daca vlanul interfetei pe care am primit e egal cu vlanul interfetei pe care trimit
                    if vlans[interface] == vlans[i] and port_states[i]==1:
                        send_to_link(i,length,data)
def forward_uinicast(interface,port_states,length,data,vlan_id,dest_mac,cam):
    interf_de_trimis=cam[dest_mac]
    if vlans[interf_de_trimis]==-1:
        # aici inseamna ca fac forward pe port trunk
        if vlans[interface]==-1 and port_states[interf_de_trimis]==1:
            # daca am primit pachetul tot pe trunk atunci il trimit direct pt ca are header-ul
            send_to_link(interf_de_trimis,length,data)
        else:
            # aici am primit pachetul pe port access si deci trebuie sa adaug eu header-ul si apoi sa trimit
            tagged_frame = data[0:12] + create_vlan_tag(vlans[interface]) + data[12:]
            if port_states[interf_de_trimis]==1:
                send_to_link(interf_de_trimis,length+4,tagged_frame)
    else:
        # aici inseamna ca trimit la host pe port access
        if vlans[interface]!=-1:
            # daca am primit pe port trunk inseamna ca am header si trebuie scos inainte sa trimit la host
            if vlans[interface] == vlans[interf_de_trimis] and port_states[interf_de_trimis]==1:
                send_to_link(interf_de_trimis,length,data)
        else:
            # aici am primit de la host si trimit tot la host deci nu am header-ul pus in pachet
            # dar trimit doar daca vlanurile interfetelor celor 2 porturi sunt egale
            if vlan_id == vlans[interf_de_trimis] and port_states[interf_de_trimis]==1:
                send_to_link(interf_de_trimis,length-4,data[0:12]+data[16:])
def initializare_stp(n,port_states):
    global priority
    global own_bridge_ID
    global root_bridge_ID
    global root_path_cost
    #imi initializez variabilele la fel ca in pseudocodul de pe ocw
    for i in range(0,n):
        if vlans[i]==-1:
            port_states[i]=0
        else:
            port_states[i]=1
    
    own_bridge_ID =  priority
    root_bridge_ID = own_bridge_ID
    root_path_cost = 0

    # apoi intrucat pt inceput e root pun porturile trunk inapoi pe LISTENING
    if own_bridge_ID==root_bridge_ID:
        for i in range(0,n):
            if vlans[i]==-1:
                port_states[i]=1
def main():
    # init returns the max interface number. Our interfaces
    # are 0, 1, 2, ..., init_ret value + 1
    switch_id = sys.argv[1]
    global interfaces
    global priority
    global own_bridge_ID
    global root_bridge_ID
    global root_path_cost
    global root_port
    num_interfaces = wrapper.init(sys.argv[2:])
    interfaces = range(0, num_interfaces)

    print("# Starting switch with id {}".format(switch_id), flush=True)
    print("[INFO] Switch MAC", ':'.join(f'{b:02x}' for b in get_switch_mac()))

    
    cam={} #dictionar folsoit pentru tabela cam a switchului in care salvez adresa mac asociata cu portul pe care se gaseste
    n=len(interfaces)
    citeste_configuratii_vlan(switch_id,n)
    #aici o sa fac initiliaziarile pt stp
    # imi declar un vector in care retin pentru fiecare port daca e in stare BLOCKING (=0) sau LISTENING (=1)
    port_states=n*[-1]
    initializare_stp(n,port_states)
    # Create and start a new thread that deals with sending BDPU
    t = threading.Thread(target=send_bdpu_every_sec)
    t.start()
    while True:
        interface, data, length = recv_from_any_link()
        # asta inseamna ca daca portul este in starea BLOCKING nu ar trebui sa ma intereseze pachetul primit asa ca il arunc
        # ca sa nu fac bucle (parte din algoritmul stp)
        if port_states[interface]==0:
            continue

        dest_mac, src_mac, ethertype, vlan_id = parse_ethernet_header(data)
        # Print the MAC src and MAC dst in human readable format
        dest_mac = ':'.join(f'{b:02x}' for b in dest_mac)
        src_mac = ':'.join(f'{b:02x}' for b in src_mac)

        

        print(f'Destination MAC: {dest_mac}')
        print(f'Source MAC: {src_mac}')
        print(f'EtherType: {ethertype}')
        print(f'Interface: {interface}')
        print("Received frame of size {} on interface {}".format(length, interface), flush=True)
        
        # aici retin atunci cand primesc un pachet in tabela cam portul asociat cu adresa mac sursa a pachetului
        if src_mac not in cam:
            cam[src_mac]=interface
 
        if is_mac_broadcast(dest_mac)==True or dest_mac not in cam:
            #trb sa trimitem pe toate porturile in afara de cel pe care a venit
            # daca e broadcast sau nu stiu portul pe care trebuie trimis
            if is_mac_multicast(dest_mac)==True:
                # aici ajung doar daca primesc un pachet bpdu
                prelucreaza_pachet_bpdu(interface, port_states, data)
            else:
                forward_broadcast(interface,port_states,length,data,vlan_id)
        else:
            # aici inseamna ca stiu pe ce port iese pachetu asa ca voi trimite doar pe acela
            forward_uinicast(interface,port_states,length,data,vlan_id,dest_mac,cam)
        

if __name__ == "__main__":
    main()
