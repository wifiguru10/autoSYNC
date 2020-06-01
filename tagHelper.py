#!/usr/bin/python3

#tagHelper

import os
import string
import sys
import meraki

tag_network_TARGET = 'autoAP'
tag_device_TARGET  = 'autoAP'
tag_device_MASTER  = 'AP:master'
tag_port_CLONE     = 'AP:clone'

class tagHelper:
    name = ""
    dashboard = None
    orgs = []
    orgs_inscope = []
    org_networks = {}
    org_networks_inscope = {}
    org_devices = {}
    org_devices_inscope = {}
    networks_inscope = [] #for lookup only
    ap_macs_inscope = []

    master_ports = {}  # {    serial : [{port},{port}]  }
    master_aps   = {}  # { networkId : [{ap},{ap}]      }

    def __init__(self):
        self.dashboard = meraki.DashboardAPI(api_key=None, base_url='https://api.meraki.com/api/v0/',log_file_prefix=__file__[:-3], print_console=False)

        self.updStart()
        return

    #returns true if the MAC/SerialNumber is inscope
    def inscope(self,s):
        oDevs = self.org_devices_inscope
        for od in oDevs:
            devs = oDevs[od]
            for d in devs:
                if d['mac'] == s.lower():
                    return True
                if d['serial'] == s.upper():
                    return True
        return False #didn't find it, return false
    

    #returns an array of network client objects
    def getNetClients(self,netId):
        nClients = self.dashboard.clients.getNetworkClients(netId,perPage=1000)
        result   = []
        for c in nClients:
            result.append(c)
        return result #end getApNetClients()

    def getNetClientsAll(self,netId):
        result = []
        oDevs = self.org_devices_inscope
        for od in oDevs:
            devices = oDevs[od]
            for d in devices:
                if d['networkId'] == netId:
                    serial = d['serial']
                    tmp =(self.dashboard.clients.getDeviceClients(serial))
                    for t in tmp:
                        result.append(t)

        return result

    def getAllClients(self,netId):
        return



    #this returns the "most common" address for a network in string - INSCOPE ONLY
    def findAddress(self,netId):
        result = ""
        for orgId in self.org_devices_inscope:
            address = {}
            devices = self.org_devices_inscope[orgId]
            for d in devices:
                if d['networkId'] == netId:
                    addy = d['address'].lower()
                    if addy != '':
                        if addy in address:
                            address[addy] += 1
                        else:
                            address[addy] = 1
            count = 0
            for a in address:
                if address[a] > count:
                    result = a
                    count = address[a]
        return result

    #same as below but for all inscope networks
    def updateAddressAll(self):
        orgs = self.getOrgNets_inscope()
        for orgId in orgs:
            nets = orgs[orgId]
            for n in nets:
                self.updateAddress(n)
        return #updateAddressAll

    #goes through all INSCOPE devices and changes the address if null or if the Master address is different
    def updateAddress(self,netId):
        newAddress = self.findAddress(netId)
        if netId in self.master_aps: #if there is a masterAP override the most common
            masterAP = self.master_aps[netId]
            newAddress = masterAP[0]['address'].lower()
#        print(f'New Address [{newAddress}]')
        for orgId in self.org_devices_inscope:
            devices = self.org_devices_inscope[orgId]
            address = {}
            for d in devices:
                if d['networkId'] == netId:
                    serial = d['serial']
                    if not d['address'].lower() == newAddress:
                        print("CONFIGURING ADDRESS")
                        if d['address'] == "" or newAddress == "":
                            self.dashboard.devices.updateNetworkDevice(netId,serial=serial,address=newAddress,moveMapMarker = False)
                        else:
                            self.dashboard.devices.updateNetworkDevice(netId,serial=serial,address=newAddress,moveMapMarker = False)
        return #updateAddress

    def getMasterPorts(self):
        self.updMaster()
        return self.master_ports

    #returns the master port config for Serial Number or Network ID
    def getMasterPort(self,target):
        mp = {}
        master_ports = self.master_ports
        if target in master_ports: #its a serial and it's the master entry
            mp = master_ports[target][0]
        else:
            #no master port, check for networkID match
            for sn in master_ports:
                mp_ports = master_ports[sn]
                for m in mp_ports:
                    if m['networkId'] == target:
                        mp = m
        return mp

    def getMasterAp(self):
        self.updMaster()
        return self.master_aps

    def getMasterAp_macs(self):
        return self.ap_macs_inscope

    def updOrgs(self):
        self.orgs = self.dashboard.organizations.getOrganizations()
        return

    #populates the orgs_inscope[] array which can be querried
    def updInscope(self):
        oNets = self.org_networks
        self.org_networks_inscope = {}
        for on in oNets:
            orgId = on
            nets  = oNets[on]
            for n in nets:
                if n is not None: 
                    if 'tags' in n:
                        if n['tags'] is not None and tag_device_TARGET in n['tags']:

                            if not on in self.orgs_inscope:
                                self.orgs_inscope.append(on) #this is where we add inscope orgs
                            if on in self.orgs_inscope:
                                if not orgId in self.org_networks_inscope:
                                    self.org_networks_inscope[orgId] = []
                                self.org_networks_inscope[orgId].append(n['id']) # this is where we add inscope networks

        return #updInscope

    #returns the device matching MAC/SerialNumber
    def getDev(self,s):
        oDevs = self.org_devices_inscope
        for od in oDevs:
            devs = oDevs[od]
            for d in devs:
                if d['mac'] == s.lower():
                    return d
                if d['serial'] == s.upper():
                    return d
        return None #didn't find it, return false

    def getDashboard(self):
        return self.dashboard

    #returns orgs
    def getOrgs(self):
        return self.orgs 

    def getOrgs_inscope(self):
        return self.orgs_inscope

    #returns all orgs and networks
    #returns { orgID : [{ networks }] }
    def getOrgNets(self):
        return self.org_networks

    def getOrgNets_inscope(self):
        return self.org_networks_inscope

    #returns all orgs and devices
    #returns { orgID : [{ devices }] }
    def getOrgDev(self):
        return self.org_devices

    #returns all orgs and devices
    #returns { orgID : [{ devices }] }
    def getOrgDev_inscope(self):
        return self.org_devices_inscope

    #updates master port configs
    def updMaster(self):
        orgDevs = self.org_devices_inscope
        self.master_ports = {}
        self.master_aps   = {}
        for orgId in orgDevs:
            devices = orgDevs[orgId]
            for d in devices:
                serial = d['serial']
                networkId = d['networkId']
                if d['model'][:2] == "MR":      #ACCESS POINTS
                    if 'tags' in d:
                        if not d['mac'] in self.ap_macs_inscope:
                            self.ap_macs_inscope.append(d['mac'])
                        if not d['tags'] is None and tag_device_MASTER in d['tags']: #AP is master
                            if not networkId in self.master_aps:
                                self.master_aps[networkId] = []
                            self.master_aps[networkId].append(d)
                elif d['model'][:2] == "MS":    #SWITCHES
                    ports = self.dashboard.switch_ports.getDeviceSwitchPorts(serial)
                    ports_is = []
                    for p in ports:
                        if 'tags' in p:
                            if not p['tags'] is None and tag_device_MASTER in p['tags']: #Port is a master port
                                #create an entry if it doesn't exist
                                if not serial in self.master_ports:
                                    self.master_ports[serial] = []
                                p['networkId'] = d['networkId'] 
                                self.master_ports[serial].append(p) #add port to master
        return #updMaster()



    def updOrgNetworks(self):
        for o in self.orgs:
            orgid = int(o['id'])
            nets = self.dashboard.networks.getOrganizationNetworks(orgid)
            self.org_networks[orgid] = nets
        self.updInscope()
        self.updateNetInscope()
        return

    def updOrgDevices(self):
        for o in self.orgs_inscope: #orgs_inscope just has orgIds not objects
            orgId = o
            orgDevs = self.dashboard.devices.getOrganizationDevices(orgId)
            self.org_devices[orgId] = orgDevs
            self.updInscope()


        #populate org_devices_inscope
        for od in self.org_devices:
            self.org_devices_inscope[od] = []
            oDevs = self.org_devices[od]
            for odis in oDevs:
                if 'tags' in odis:
                    if odis['tags'] is not None and tag_device_TARGET in odis['tags']:
                        if odis['networkId'] in self.networks_inscope:
                            self.org_devices_inscope[od].append(odis)

        return #updOrgDevices

    #returns all the network IDS inscope
    def updateNetInscope(self):
        nets_inscope = self.getOrgNets_inscope()
        self.networks_inscope = []
        for orgid in nets_inscope:
            for n in nets_inscope[orgid]:
                self.networks_inscope.append(n)
        return

    def getNetInscope(self):
        return self.networks_inscope


    #once update, only on start
    def updStart(self):
        self.updAll()
        self.updateAddressAll()
        return #updStart

    #less frequent update, more resource intensive
    def updAll(self):
        self.updOrgs()
        self.updOrgNetworks()
        self.update()
        return #updAll

    #more frequent update #INSCOPE ONLY
    def update(self):
        self.updOrgDevices()
        self.updMaster()
        return #update


#END OF CLASS


if __name__ == "__main__":
    # main(sys.argv[1:])
    print("HEY")

