__author__ = "Akshay Mane"

import json
import os
import sys
from functools import wraps

import requests
import urllib3
import logging
from typing import Dict, List
from os.path import join, normpath

# Disable insecure connections warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FortiManager:
    """
    This class will include all the methods used for executing the api calls on FortiManager.
    """

    def __init__(self, host, username="admin", password="admin", adom="root", protocol="https", verify=True,
                 proxies={}):
        self.protocol = protocol
        self.host = host
        self.username = username
        self.password = password
        self.adom = adom
        self.sessionid = None
        self.session = None
        self.verify = verify
        self.proxies = proxies
        if protocol == "http":
            self.verify = False
        self.base_url = f"{protocol}://{self.host}/jsonrpc"

    # Login Method
    def login(self):
        """
        Log in to FortiManager with the details provided during object creation of this class
        :return: Session
        """

        if self.sessionid is None or self.session is None:
            self.session = requests.session()
            # check for explicit proxy handling
            # proxies = False means force not using proxies
            # proxies set like described in https://2.python-requests.org/en/latest/user/advanced/#proxies
            #  means override environment proxy settings
            # otherwise use environment settings
            if self.proxies is False:
                self.session.trust_env = False

            elif len(self.proxies) != 0:
                self.session.proxies.update(self.proxies)
            else:
                self.session.trust_env = True  # obsolete as it is default
            payload = \
                {
                    "method": "exec",
                    "params":
                        [
                            {
                                "data": {
                                    "passwd": self.password,
                                    "user": self.username
                                },
                                "url": "sys/login/user"
                            }
                        ],
                    "session": self.sessionid
                }
            login = self.session.post(
                url=self.base_url, json=payload, verify=self.verify)
            if login.json()["result"][0]["status"]["message"] == "No permission for the resource":
                return self.session
            elif "session" in login.json():
                self.sessionid = login.json()["session"]
                return self.session

        else:
            return self.session

    def logout(self):
        """
        Logout from FortiManager
        :return: Response of status code with data in JSON Format
        """
        session = requests.session()
        payload = \
            {
                "method": "exec",
                "params":
                    [
                        {
                            "url": "sys/logout"
                        }
                    ],
                "session": self.sessionid
            }
        logout = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return logout.json()["result"]

    # Adoms Methods
    def get_adoms(self, name=False):
        """
        Get all adoms from the FortiManager
        :param name: Can get specific adom using name as a filter
        :return: Response of status code with data in JSON Format
        """
        url = "dvmdb/adom"
        if name:
            url = f"dvmdb/adom/{name}"
        session = self.login()
        payload = \
            {
                "method": "get",
                "params":
                    [
                        {
                            "url": url,
                            "option": "object member"
                        }
                    ],
                "session": self.sessionid
            }
        get_adoms = session.post(url=self.base_url, json=payload, verify=False)
        return get_adoms.json()["result"]

    def get_devices(self):
        """
        :return: returns list of devices added in FortiManager
        """
        session = self.login()
        payload = {"method": "get", "params": [
            {"url": f"/dvmdb/adom/{self.adom}/device/"}]}
        payload.update({"session": self.sessionid})
        get_devices = session.post(
            url=self.base_url, json=payload, verify=False)
        return get_devices.json()

    def add_device(self, ip_address, username, password, name, description=False):
        session = self.login()
        payload = \
            {
                "method": "exec",
                "params": [
                    {"url": "dvm/cmd/add/device",
                     "data": {"adom": f"{self.adom}", "flags": ["create_task", "nonblocking"],
                              "device": {"adm_pass": f"{password}", "adm_usr": f"{username}", "desc": f"{description}",
                                         "ip": f"{ip_address}",
                                         "name": f"{name}", "mgmt_mode": 3}}}]}
        payload.update({"session": self.sessionid})
        add_device = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return add_device.json()

    def add_model_device(self, name, serial_no, username="admin", password="", os_ver=6, mr=4, os_type="fos",
                        platform=""):
        # remove nonblocking from flags. With non-blocking the returned status looks like this even when the job failed, 
        # since the creation status of the job is returned:
        # [{'data': {'pid': 20172, 'taskid': 3194}, 'status': {'code': 0, 'message': 'OK'}, 'url': 'dvm/cmd/add/device'}]
        #
        # without nonblocking the failure reason is returned: 
        # [{'status': {'code': -20010, 'message': 'Serial number already in use'}, 'url': 'dvm/cmd/add/device'}]
        session = self.login()
        payload = {
            "method": "exec",
            "params": [
                {
                    "url": "dvm/cmd/add/device",
                    "data": {
                        "adom": self.adom,
                        "flags": [
                            "create_task"
                        ],
                        "device": {
                            "name": name,
                            "adm_usr": username,
                            "adm_pass": password,
                            "flags": 67371040,
                            "sn": serial_no,
                            "platform_str": platform,
                            "os_ver": os_ver,
                            "mr": mr,
                            "os_type": os_type,
                            "mgmt_mode": "fmg",
                            "device_action": "add_model",
                        }
                    }
                }
            ]
        }
        payload.update({"session": self.sessionid})
        add_model_device = session.post(
            url=self.base_url, json=payload, verify=False)
        return add_model_device.json()["result"]

    # Policy Package Methods
    def get_policy_packages(self, name=False, ):
        """
        Get all the policy packages configured on FortiManager
        :param name: Can get specific package using name as a filter
        :return: Response of status code with data in JSON Format
        """
        url = f"pm/pkg/adom/{self.adom}/"
        if name:
            url = f"pm/pkg/adom/{self.adom}/{name}"
        session = self.login()
        payload = \
            {
                "method": "get",
                "params":
                    [
                        {
                            "url": url
                        }
                    ],
                "session": self.sessionid
            }
        get_packages = session.post(
            url=self.base_url, json=payload, verify=False)
        return get_packages.json()["result"]

    def add_policy_package(self, name):
        """
        Can add your own policy package in FortiManager
        :param name: Specific the Package Name
        :return: Response of status code with data in JSON Format
        """
        url = f"pm/pkg/adom/{self.adom}/"
        session = self.login()
        payload = \
            {
                "method": "set",
                "params":
                    [
                        {
                            "data": [{
                                "name": name,
                                "type": "pkg"
                            }, ],
                            "url": url
                        }
                    ],
                "session": self.sessionid
            }
        add_package = session.post(
            url=self.base_url, json=payload, verify=False)
        return add_package.json()["result"]

    def add_install_target(self, device_name, pkg_name, vdom: str = "root"):
        """
        Add a device to installation target list of the policy package
        :param device_name: name of the device
        :param pkg_name: name of the policy package
        :param vdom: name of the vdom (default=root)
        :return: returns response from FortiManager api whether is was a success or failure.
        """
        session = self.login()
        payload = \
            {"method": "add",
             "params": [{"url": f"pm/pkg/adom/{self.adom}/{pkg_name}/scope member",
                         "data": [{"name": f"{device_name}",
                                   "vdom": f"{vdom}"}]}]}
        payload.update({"session": self.sessionid})
        add_installation_target = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return add_installation_target.json()

    def get_meta_data(self):
        """
        Get all the meta tags present in the FortiManager
        :return: returns meta tags present in FortiManager
        """
        session = self.login()
        payload = {"method": "get", "params": [
            {"url": "/dvmdb/_meta_fields/device"}]}
        payload.update({"session": self.sessionid})
        get_meta = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return get_meta.json()

    def add_meta_data(self, name, importance=0, status=1):
        """
        Add a meta tag in the FortiManager.
        :param name: name of the meta tag
        :param importance: importance of meta tag
        :param status: status of meta tag whether it should be active(1) or disabled(0)
        :return: returns response from FortiManager API whether the request was successful or not.!
        """
        session = self.login()
        payload = {"method": "add",
                   "params": [
                       {"url": "/dvmdb/_meta_fields/device",
                        "data": {"importance": importance, "length": 255, "name": f"{name}",
                                 "status": status}}]}
        payload.update({"session": self.sessionid})
        get_meta = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return get_meta.json()

    def assign_meta_to_device(self, device, meta_data=dict):
        """
        Assign a meta tag to the device
        :param device: name of the device
        :param meta_data: A dictionary of meta name:value pairs (Note, values must be strings, not integers!)
        :return: returns response from FortiManager API whether the request was successful or not.!
        """
        session = self.login()
        payload = {"method": "update",
                   "params": [{"url": f"/dvmdb/adom/root/device/{device}",
                               "data": {"name": f"{device}", "meta fields": meta_data}}]}
        payload.update({"session": self.sessionid})
        assign_meta = session.post(
            self.base_url, json=payload, verify=self.verify)
        return assign_meta.json()

    def assign_meta_to_device_vdom(self, device, vdom, meta_name, meta_value):
        """
        Assign a meta tag to the device
        :param device: name of the device
        :param vdom: Specify the Vdom
        :param meta_name: name of the meta tag
        :param meta_value: value of the meta tag
        :return: returns response from FortiManager API whether the request was successful or not.!
        """
        session = self.login()
        payload = {"method": "update",
                   "params": [{"url": f"/dvmdb/adom/{self.adom}/device/{device}/vdom/{vdom}",
                               "data": {"name": f"{device}", "meta fields": {f"{meta_name}": f"{meta_value}"}}}]}
        payload.update({"session": self.sessionid})
        assign_meta_vdom = session.post(
            self.base_url, json=payload, verify=self.verify)
        return assign_meta_vdom.json()

    def set_prefer_img_ver_to_model_device(self, device, vdom, prefer_img_ver):
        """
        Set preferred image version to the device
        :param device: name of the device
        :param prefer_img_ver: preferred image version, e.g. 7.0.6-b366
        :return: returns response from FortiManager API whether the request was successful or not.!
        """
        session = self.login()
        payload = {"method": "update",
                   "params": [{"url": f"/dvmdb/adom/{self.adom}/device/{device}",
                               "data": {"name": f"{device}", "prefer_img_ver": f"{prefer_img_ver}"}}]}
        payload.update({"session": self.sessionid})
        set_image_ver = session.post(
            self.base_url, json=payload, verify=self.verify)
        return set_image_ver.json()       

    def associate_cli_template_to_device(self, device, template, vdom="root", provision="disable"):
        """
        Associate cli template to device
        :param device: name of the device
        :param template: name of template group
        :param vdom: vdom the cli template should be associated to, by default 'root'
        :param provision: by default 'disable', set to 'enable' if assigning pre-run template
        :return: returns response from FortiManager API whether the request was successful or not.!
        """
        #First, we must get the currently associated devices.
        session = self.login()
        payload1 = {"method": "get",
                   "params": [{"url": f"/pm/config/adom/{self.adom}/obj/cli/template/{template}",
                               "option": "scope member"}]}
        payload1.update({"session": self.sessionid})
        current_members = session.post(
            self.base_url, json=payload1, verify=self.verify).json()
        #Check if there template has been assigned to any firewalls and append new firewall 
        #to the list. If not, initiate the list and append.
        if "scope member" in current_members["result"][0]["data"]:
            members = current_members["result"][0]["data"]["scope member"]
        else:
            members = []
        members.append({"name": f"{device}", "vdom": vdom})
        #Second, add the new device to the group, along with the old devices
        payload2 = {"method": "update",
                   "params": [{"url": f"/pm/config/adom/{self.adom}/obj/cli/template/{template}",
                               "data": {"name": f"{template}", "provision": provision, "scope member": members}}]}
        payload2.update({"session": self.sessionid})
        associate_clitemplate = session.post(
            self.base_url, json=payload2, verify=self.verify)
        return associate_clitemplate.json()     

    def associate_prov_template_to_device(self, device, template, vdom="root"):
        """
        Associate cli template to device
        :param device: name of the device
        :param template: name of template group
        :param vdom: vdom the cli template should be associated to, by default 'root'
        :return: returns response from FortiManager API whether the request was successful or not.!
        """
        #First, we must get the currently associated devices.
        session = self.login()
        payload1 = {"method": "get",
                   "params": [{"url": f"/pm/wanprof/adom/{self.adom}/{template}",
                               "option": "scope member"}]}
        payload1.update({"session": self.sessionid})
        current_members = session.post(
            self.base_url, json=payload1, verify=self.verify).json()
        #Check if there template has been assigned to any firewalls and append new firewall 
        #to the list. If not, initiate the list and append.
        if "scope member" in current_members["result"][0]["data"]:
            members = current_members["result"][0]["data"]["scope member"]
        else:
            members = []
        members.append({"name": f"{device}", "vdom": vdom})
        #Second, add the new device to the group, along with the old devices
        payload2 = {"method": "update",
                   "params": [{"url": f"/pm/wanprof/adom/{self.adom}/{template}",
                               "data": {"name": f"{template}", "scope member": members}}]}
        payload2.update({"session": self.sessionid})
        associate_clitemplate = session.post(
            self.base_url, json=payload2, verify=self.verify)
        return associate_clitemplate.json()     

    def associate_cli_templategroup_to_device(self, device, tmplgrp):
        """
        Associate cli template group to device
        :param device: name of the device
        :param tmplgrp: name of template group
        :return: returns response from FortiManager API whether the request was successful or not.!
        """
        #First, we must get the currently associated devices.
        session = self.login()
        payload1 = {"method": "get",
                   "params": [{"url": f"/pm/config/adom/{self.adom}/obj/cli/template-group/{tmplgrp}",
                               "option": "scope member"}]}
        payload1.update({"session": self.sessionid})
        current_members = session.post(
            self.base_url, json=payload1, verify=self.verify).json()
        #Check if there template has been assigned to any firewalls and append new firewall 
        #to the list. If not, initiate the list and append.
        if "scope member" in current_members["result"][0]["data"]:
            members = current_members["result"][0]["data"]["scope member"]
        else:
            members = []
        members.append({"name": f"{device}", "vdom": "root"})
        #Second, add the new device to the group, along with the old devices
        payload2 = {"method": "update",
                   "params": [{"url": f"/pm/config/adom/{self.adom}/obj/cli/template-group",
                               "data": {"name": f"{tmplgrp}", "scope member": members}}]}
        payload2.update({"session": self.sessionid})
        associate_tmplgrp = session.post(
            self.base_url, json=payload2, verify=self.verify)
        return associate_tmplgrp.json()       

    # Firewall Object Methods
    def get_firewall_address_objects(self, name=False):
        """
        Get all the address objects data stored in FortiManager
        :return: Response of status code with data in JSON Format
        """
        url = f"pm/config/adom/{self.adom}/obj/firewall/address"
        if name:
            url = f"pm/config/adom/{self.adom}/obj/firewall/address/{name}"
        session = self.login()
        payload = \
            {
                "method": "get",
                "params": [
                    {
                        "url": url
                    }
                ],
                "session": self.sessionid
            }
        get_address_objects = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return get_address_objects.json()["result"]

    def add_firewall_address_object(self, name, subnet: list, associated_interface="any", object_type=0,
                                    allow_routing=0):
        """
        Create an address object using provided info
        :param name: Enter object name that is to be created
        :param associated_interface: Provide interface to which this object belongs if any. {Default is kept any}
        :param subnet: Enter the subnet in a list format eg.["1.1.1.1", "255.255.255.255"]
        :param object_type:
        :param allow_routing: Set routing if needed
        :return: Response of status code with data in JSON Format
        """
        session = self.login()
        payload = {
            "method": "add",
            "params": [{"data": {
                "allow-routing": allow_routing,
                "associated-interface": associated_interface,
                "name": name,
                "subnet": subnet,
                "type": object_type},
                "url": f"pm/config/adom/{self.adom}/obj/firewall/address"}],
            "session": self.sessionid}

        add_address_object = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return add_address_object.json()["result"]

    def add_dynamic_object(self, name, device, subnet, comment=None):
        """
        Add per device mapping in address object.
        :param name: name of the address object.
        :param device: name of the device which is to be mapped in this object
        :param subnet: subnet for device that is to be mapped in this object.
        Either a string with subnet/bitmask (e.g. "10.10.10.0/24" or list with subnet and mask (e.g. ["10.10.10.0", "255.255.255.0"])
        :param comment: comment
        :return: returns response of the request from FortiManager.
        """
        session = self.login()
        add_obj = self.add_firewall_address_object(
            name, subnet=["0.0.0.0", "255.255.255.255"])
        payload = {
            "method": "add",
            "params": [{"url": f"pm/config/adom/root/obj/firewall/address/{name}/dynamic_mapping",
                        "data": [{"_scope": [{"name": f"{device}", "vdom": "root"}],
                                  "subnet": subnet,
                                  "comment": f"{comment}",
                                  }]}],
            "session": self.sessionid}
        add_dynamic_obj = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return [add_obj, add_dynamic_obj.json()["result"]]

    def update_dynamic_object(self, name, device, subnet: list, do="add", comment=None):
        """
        Update the per mapping settings of the address object.
        :param name: name of the object that needs to be updated.
        :param device: name of the device that needs to be added/updated
        :param subnet: updated subnet of the device that needs to be mapped
        :param do: if parameter do is set to "add" it will update it. If it is set to "remove" it will be deleted.
        :param comment: add comment if you want.
        :return: return result of the request from FortiManager.
        """
        session = self.login()
        payload = {
            "params": [{"url": f"pm/config/adom/root/obj/firewall/address/{name}/dynamic_mapping",
                        "data": [{"_scope": [{"name": f"{device}", "vdom": "root"}],
                                  "subnet": subnet,
                                  "comment": f"{comment}",
                                  }]}],
            "session": self.sessionid}
        if do == "add":
            payload.update(method="update")
        elif do == "remove":
            payload.update(method="delete")
        update_dynamic_obj = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return update_dynamic_obj.json()["result"]

    def update_firewall_address_object(self, name, **data):
        """
        Get the name of the address object and update it with your data
        :param name: Enter the name of the object that needs to be updated
        :param data: You can get the **kwargs parameters with "show_params_for_object_update()" method
        :return: Response of status code with data in JSON Format
        """
        data = self.make_data(_for="object", **data)
        session = self.login()
        payload = \
            {
                "method": "update",
                "params": [
                    {
                        "data": data,
                        "url": f"pm/config/adom/{self.adom}/obj/firewall/address/{name}"
                    }
                ],
                "session": self.sessionid
            }
        payload = repr(payload)
        update_firewall_object = session.post(
            url=self.base_url, data=payload, verify=self.verify)
        return update_firewall_object.json()["result"]

    def delete_firewall_address_object(self, object_name):
        """
        Delete the address object if no longer needed using object name
        :param object_name: Enter the Object name you want to delete
        :return: Response of status code with data in JSON Format
        """
        session = self.login()
        payload = \
            {
                "method": "delete",
                "params": [
                    {
                        "url": f"pm/config/adom/{self.adom}/obj/firewall/address/{object_name}"
                    }
                ],
                "session": self.sessionid
            }
        delete_address_object = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return delete_address_object.json()["result"]

    # Firewall Address Groups Methods
    def get_address_groups(self, name=False):
        """
        Get the address groups created in your FortiManager
        :param name: You can filter out the specific address group which you want to see
        :return: Response of status code with data in JSON Format
        """
        session = self.login()
        url = f"pm/config/adom/{self.adom}/obj/firewall/addrgrp"
        if name:
            url = f"pm/config/adom/{self.adom}/obj/firewall/addrgrp/{name}"
        payload = \
            {
                "method": "get",
                "params": [
                    {
                        "url": url
                    }
                ],
                "session": self.sessionid
            }
        get_address_group = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return get_address_group.json()["result"]

    def add_address_group(self, name, members=list):
        """
        Create your own group with just 2 parameters
        :param name: Enter the name of the address group                eg."Test_Group"
        :param members: pass your object names as members in a list     eg. ["LAN_10.1.1.0_24, "INTERNET"]
        :return: Response of status code with data in JSON Format
        """
        session = self.login()
        payload = \
            {
                "method": "add",
                "params": [
                    {
                        "data": {
                            "name": name,
                            "member": members,
                        },
                        "url": f"pm/config/adom/{self.adom}/obj/firewall/addrgrp"
                    }
                ],
                "session": self.sessionid
            }
        add_address_group = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return add_address_group.json()["result"]

    def update_address_group(self, name, object_name, do="add"):
        """
        Update Members of the Address group
        :param name: Specify the name of the Address group you want to update
        :param object_name: Specify name of the object you wish to update(add/remove) in Members List
        :param do: Specify if you want to add or remove the object from the members list
                    do="add"    will add the object in the address group
                    do="remove" will remove the object from address group
        :return: Response of status code with data in JSON Format
        """
        session = self.login()
        get_addr_group = self.get_address_groups(name=name)
        members = get_addr_group[0]['data']['member']
        if do == "add":
            members.append(object_name)
        elif do == "remove":
            members.remove(object_name)

        payload = \
            {
                "method": "update",
                "params": [
                    {
                        "data": {
                            "member": members,
                        },
                        "url": f"pm/config/adom/{self.adom}/obj/firewall/addrgrp/{name}"
                    }
                ],
                "session": self.sessionid
            }
        update_address_group = session.post(
            url=self.base_url, json=payload, verify=False)
        return update_address_group.json()["result"]

    def delete_address_group(self, name):
        """
        Delete the Address group if no longer needed
        :param name: Specify the name of the address you wish to delete
        :return: Response of status code with data in JSON Format
        """
        session = self.login()
        payload = \
            {
                "method": "delete",
                "params": [
                    {
                        "data": {
                        },
                        "url": f"pm/config/adom/{self.adom}/obj/firewall/addrgrp/{name}"
                    }
                ],
                "session": self.sessionid
            }
        delete_address_group = session.post(
            url=self.base_url, json=payload, verify=False)
        return delete_address_group.json()["result"]

    def add_dynamic_group_object(self, name, device, subnets=list, comment=None):
        """
        Add per device mapping in address object.
        :param name: name of the address object.
        :param device: name of the device which is to be mapped in this object
        :param subnets: A list of (existing) object names for device that is to be mapped in this object.
        :param comment: comment
        :return: returns response of the request from FortiManager.
        """
        session = self.login()
#        add_obj = self.add_firewall_address_object(
#            name, subnet=["0.0.0.0", "255.255.255.255"])
        payload = {
            "method": "add",
            "params": [{"url": f"pm/config/adom/{self.adom}/obj/firewall/addrgrp/{name}/dynamic_mapping",
                        "data": [{"_scope": [{"name": f"{device}", "vdom": "root"}],
                                  "member": subnets,
                                  "comment": f"{comment}",
                                  }]}],
            "session": self.sessionid}
        add_dynamic_grp_obj = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return add_dynamic_grp_obj.json()["result"]

    # Firewall Virtual IP objects
    def get_firewall_vip_objects(self, name=False):
        """
        Get all the vip objects data stored in FortiManager
        :return: Response of status code with data in JSON Format
        """
        url = f"pm/config/adom/{self.adom}/obj/firewall/vip"
        if name:
            url = f"pm/config/adom/{self.adom}/obj/firewall/vip/{name}"
        session = self.login()
        payload = \
            {
                "method": "get",
                "params": [
                    {
                        "url": url
                    }
                ],
                "session": self.sessionid
            }
        get_vip_objects = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return get_vip_objects.json()["result"]

    # Firewall Interfaces
    def get_device_interfaces(self, device):
        """
        Get interface details from the devices.
        :param device: Specify name of the device.
        """
        session = self.login()
        payload = \
            {
                "method": "exec",
                "params": [
                    {"url": "sys/proxy/json",
                     "data": {"target": [f"adom/{self.adom}/device/{device}"], "action": "get",
                              "resource": "/api/v2/monitor/system/interface/select?&global=1&include_vlan=1"}}]}
        payload.update(session=self.sessionid)
        get_interfaces = session.post(url=self.base_url, json=payload, verify=self.verify)
        return get_interfaces.json()["result"]

    # Services
    def get_services(self):
        """
                Get interface details from the devices.
                :param device: Specify name of the device.
                """
        session = self.login()
        payload = \
            {"method": "get",
             "params": [{"url": f"pm/config/adom/{self.adom}/obj/firewall/service/custom/Custom_Service_1"}]}

        payload.update(session=self.sessionid)
        services = session.post(url=self.base_url, json=payload, verify=self.verify)
        return services.json()["result"]

    def get_service(self, name):
        """
        Get interface details from the devices.
        :param name: Specify name of the device.
        """
        session = self.login()
        payload = \
            {"method": "get", "params": [{"url": f"pm/config/adom/{self.adom}/obj/firewall/service/custom/{name}"}]}

        payload.update(session=self.sessionid)
        service = session.post(url=self.base_url, json=payload, verify=self.verify)
        return service.json()["result"]

    # Firewall Policies Methods
    def get_firewall_policies(self, policy_package_name="default", policyid=False):
        """
        Get the firewall policies present in the policy package
        :param policy_package_name: Enter the policy package name
        :param policyid: Can filter and get the policy you want using policyID
        :return: Response of status code with data in JSON Format
        """
        url = f"pm/config/adom/{self.adom}/pkg/{policy_package_name}/firewall/policy/"
        if policyid:
            url = url + str(policyid)
        session = self.login()
        payload = {
            "method": "get",
            "params": [
                {
                    "url": url
                }
            ],
            "session": self.sessionid
        }
        get_firewall_policies = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return get_firewall_policies.json()["result"]

    def add_firewall_policy(self, policy_package_name: str, name: str, source_interface: str,
                            source_address: str, destination_interface: str, destination_address: str,
                            service: str, nat='disable', schedule="always", action=1, logtraffic=2):
        """
        Create your own policy in FortiManager using the instance parameters.
        :param policy_package_name: Enter the name of the policy package                eg. "default"
        :param name: Enter the policy name in a string format                           eg. "Test Policy"
        :param source_interface: Enter the source interface in a string format          eg. "port1"
        :param source_address: Enter the src. address object name in string format      eg. "LAN_10.1.1.0_24"
        :param destination_interface: Enter the source interface in a string format     eg. "port2"
        :param destination_address: Enter the dst. address object name                  eg. "WAN_100.25.1.63_32"
        :param service: Enter the service you want to permit or deny in string          eg. "ALL_TCP"
        :param nat: Enter enable or disable for nat in a string format                  eg. 'disable'
        :param schedule: Schedule time is kept 'always' as default.
        :param action: Permit(1) or Deny(0) the traffic. Default is set to Permit.
        :param logtraffic: Specify if you need to log all traffic or specific in int format.
                            logtraffic=0: Means No Log
                            logtraffic=1 Means Log Security Events
                            logtraffic=2 Means Log All Sessions
        :return: Response of status code with data in JSON Format
        """
        session = self.login()
        payload = {
            "method": "add",
            "params": [
                {
                    "data": {
                        "dstaddr": destination_address,
                        "dstintf": destination_interface,
                        "logtraffic": logtraffic,
                        "name": name,
                        "schedule": schedule,
                        "service": service,
                        "srcaddr": source_address,
                        "srcintf": source_interface,
                        "action": action,
                        "nat": nat
                    },
                    "url": f"pm/config/adom/{self.adom}/pkg/{policy_package_name}/firewall/policy/"
                }
            ],
            "session": self.sessionid
        }
        add_policy = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return add_policy.json()

    def update_firewall_policy(self, policy_package_name, policyid, **data):
        """
        Update your policy with your specific needs
        :param policy_package_name: Enter the policy package name in which you policy belongs
        :param policyid: Enter the Policy ID you want to edit
        :param data: You can get the **kwargs parameters with "show_params_for_policy_update()" method
        :return: Response of status code with data in JSON Format
        """
        data = self.make_data(**data)
        session = self.login()
        payload = \
            {
                "method": "update",
                "params": [
                    {
                        "data": data,
                        "url": f"pm/config/adom/{self.adom}/pkg/{policy_package_name}/firewall/policy/{policyid}"
                    }
                ],
                "session": self.sessionid
            }
        update_policy = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return update_policy.json()["result"]

    def delete_firewall_policy(self, policy_package_name, policyid):
        """
        Delete the policy if not is use with the policyID
        :param policy_package_name: Enter the policy package name in which you policy belongs
        :param policyid: Enter the policy ID of the policy you want to delete
        :return: Response of status code with data in JSON Format
        """
        session = self.login()
        payload = \
            {
                "method": "delete",
                "params": [
                    {
                        "url": f"pm/config/adom/{self.adom}/pkg/{policy_package_name}/firewall/policy/{policyid}"
                    }
                ],
                "session": self.sessionid
            }
        delete_policy = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return delete_policy.json()["result"]

    def move_firewall_policy(self, policy_package_name, move_policyid=int, option="before", policyid=int):
        """
        Move the policy as per your needs
        :param policy_package_name: Enter the policy package name in which you policy belongs
        :param move_policyid: Enter the policy ID of the policy you want to move
        :param option: Specify if you want to move above("before") the target policy or below("after") {default: before}
        :param policyid: Specify the target policy
        :return: Response of status code with data in JSON Format
        """
        session = self.login()
        payload = \
            {
                "method": "move",
                "params": [
                    {
                        "url": f"pm/config/adom/{self.adom}/pkg/{policy_package_name}/firewall/policy/{move_policyid}",
                        "option": option,
                        "target": str(policyid)
                    }
                ],
                "session": self.sessionid
            }
        move_policy = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return move_policy.json()["result"]

    def install_policy_package(self, package_name, scope, flags=List):
        """
        Install the policy package on your Forti-gate Firewalls
        :param package_name: Enter the package name you wish to install
        :return: Response of status code with data in JSON Format
        """
        #flags=[]
        session = self.login()
        payload = \
            {
                "method": "exec",
                "params": [
                    {
                        "data": {
                            "adom": f"{self.adom}",
                            "pkg": f"{package_name}",
                            "flags": flags,
                            "scope": [scope]
                        },
                        "url": "securityconsole/install/package"
                    }
                ],
                "session": self.sessionid
            }
        print(payload)
        install_package = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return install_package.json()["result"]

    def install_device(self, scope=list):
        """
        Install the policy package on your Forti-gate Firewalls
        :param package_name: Enter the package name you wish to install
        :return: Response of status code with data in JSON Format
        """
        session = self.login()
        payload = \
            {
                "method": "exec",
                "params": [
                    {
                        "data": {
                            "adom": f"{self.adom}",
                            "scope": scope
                        },
                        "url": "securityconsole/install/device"
                    }
                ],
                "session": self.sessionid
            }
        install_package = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return install_package.json()["result"]

    @staticmethod
    def make_data(_for="policy", **kwargs):
        object_maps = \
            {
                "allow_routing": "allow-routing",
                "associated_interface": "associated-interface",
                "comment": "comment",
                "object_name": "name",
                "subnet": "subnet",
                "object_type": "type"
            }
        policy_maps = \
            {
                "name": "name",
                "source_interface": "srcintf",
                "source_address": "srcaddr",
                "destination_interface": "dstintf",
                "destination_address": "dstaddr",
                "service": "service",
                "schedule": "schedule",
                "action": "action",
                "logtraffic": "logtraffic",
                "comment": "comments"
            }

        data = {}
        for key, value in kwargs.items():
            if _for == "policy":
                key = key.replace(key, policy_maps[key])
            elif _for == "object":
                key = key.replace(key, object_maps[key])
            else:
                logging.error(
                    "The parameter '_for' shouldn't be anything except 'policy' or 'object'")
            data.update({key: value})

        return data

    @staticmethod
    def show_params_for_object_update():
        docs = \
            """
        Parameters to create/update address object:

        PARAMETERS                   FIREWALL OBJECT SETTINGS
        allow_routing(int)          : Static Route Configuration
        associated_interface(str)   : Interface
        comment(str)                : Comments
        object_name(str)            : Address Name
        subnet[list]                : IP/Netmask
        object_type(int)            : Type
        """
        return docs

    @staticmethod
    def show_params_for_policy_update():
        docs = \
            """
        Parameters to create/update Policy:

        PARAMETERS                       FIREWALL POLICY SETTINGS
        name(str)                       : Name
        source_interface(str)           : Incoming Interface
        source_address(str)             : Source Address
        destination_interface(str)      : Destination Interface
        destination_address(str)        : Destination Address
        service(str)                    : Service
        schedule(str)                   : Schedule
        action(int)                     : Action
        logtraffic(int)                 : Log Traffic
        comment(str)                    : Comments
        """
        return docs

    def custom_api(self, payload):
        """
        Execute an API call manually by defining the payload
        :param payload: specify the valid payload in a dict.
        :return: returns response of the API call from FortiManager
        """
        session = self.login()
        payload = payload
        payload.update({"session": self.sessionid})
        custom_api = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return custom_api.json()

    def set_adom(self, adom=None):
        self.adom = adom

    # Scripts api calls
    def create_script(self, name: str, script_content: str, target: int = 0):
        """
        Create a script template and store it on FortiManager
        :param name: Specify a name for the script
        :param script_content: write the cli commands
        :param target:
                If Target = 0 than script runs on Device database
                If Target = 1 than script runs on Remote FortiGate CLI
                If Target = 2 than script runs on Policy package or Adom Database
        Default value is set to 0
        """

        session = self.login()
        payload = \
            {
                "method": "add",
                "params": [{"url": f"/dvmdb/adom/{self.adom}/script/",
                            "data": {"name": name, "content": script_content, "target": target, "type": 1}}],
                "session": self.sessionid
            }
        create_script = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return create_script.json()["result"]

    def get_all_scripts(self):
        """
        Get all script templates from FortiManager
        """

        session = self.login()
        payload = \
            {
                "method": "get",
                "params": [{"url": f"/dvmdb/adom/{self.adom}/script/"}],
                "session": self.sessionid
            }
        create_script = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return create_script.json()["result"]

    def update_script(self, oid: int, name: str, script_content: str, target: int = 0):
        """
        Create a script template and store it on FortiManager
        :param oid: Specify the script OID which needs to be updated
        :param name: Specify a name for the script
        :param script_content: write the cli commands
        :param target:
                If Target = 0 than script runs on Device database
                If Target = 1 than script runs on Remote FortiGate CLI
                If Target = 2 than script runs on Policy package or Adom Database
        Default value is set to 0
        """

        session = self.login()
        payload = \
            {
                "method": "update",
                "params": [{"url": f"/dvmdb/adom/{self.adom}/script/",
                            "data":
                                {"content": script_content,
                                 "desc": "",
                                 "filter_build": -1,
                                 "filter_device": 0,
                                 "filter_hostname": "",
                                 "filter_ostype": 0,
                                 "filter_osver": -1,
                                 "filter_platform": "",
                                 "filter_serial": "",
                                 "name": name,
                                 "oid": oid,
                                 "script_schedule": None,
                                 "target": target, "type": 1}}],
                "session": self.sessionid
            }
        update_script = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return update_script.json()["result"]

    def delete_script(self, name: str):
        """
        Create a script template and store it on FortiManager
        :param name: Specify the script name which needs to be deleted
        """

        session = self.login()
        payload = \
            {
                "method": "delete",
                "params": [{"url": f"/dvmdb/adom/{self.adom}/script/", "confirm": 1,
                            "filter": ["name", "in", name]}],
                "session": self.sessionid
            }
        delete_script = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return delete_script.json()["result"]

    def run_script_on_multiple_devices(self, script_name: str, devices: List[dict]):
        """
        Create a script template and store it on FortiManager
        :param devices: Specify devices in a list of dictionaries.
                eg. devices=[{"name": "FortiGateVM64-1", "vdom": "root"},
                             {"name": "FortiGateVM64-2", "vdom": "test"}
                             {"name": "FortiGateVM64-3", "vdom": "root"}]
        :param script_name: Specify the script name that should be executed on the specified devices
        """

        session = self.login()
        payload = \
            {
                "method": "exec",
                "params": [{
                    "data": {"adom": self.adom,
                             "scope": devices,
                             "script": script_name},
                    "url": "/dvmdb/adom/root/script/execute"}],
                "session": self.sessionid
            }
        run_script = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return run_script.json()["result"]

    def run_script_on_single_device(self, script_name: str, device_name: str, vdom: str):
        """
        Create a script template and store it on FortiManager
        :param device_name: Specify device name.
        :param vdom: Specify the Vdom
        :param script_name: Specify the script name that should be executed on the specified devices
        """

        session = self.login()
        payload = \
            {
                "method": "exec",
                "params": [{
                    "data": {"adom": self.adom,
                             "scope": {"name": device_name, "vdom": vdom},
                             "script": script_name},
                    "url": "/dvmdb/adom/root/script/execute"}],
                "session": self.sessionid
            }

        run_script = session.post(
            url=self.base_url, json=payload, verify=self.verify)
        return run_script.json()["result"]

    def backup_config_of_fortiGate_to_tftp(self, tftp_ip, path, script_name, filename, device_name, vdom="root"):
        """
        A small function to backup configuration on FortiGates from FortiManager and store it in TFTP Server.
        :param tftp_ip: Specify TFTP Server IP
        :param path: Specify the path to store the config
        :param script_name: Specify the Script name
        :param filename: Specify the name of the backup file
        :param device_name: Specify the name of the device
        :param vdom: Specify the Vdom
        """
        result = []
        full_path = normpath(join(path, filename)).replace("\\", "/")
        cli_command = f"execute backup config tftp {full_path} {tftp_ip}"
        logging.info("Creating a Script Template in FortiManager")
        result.append(
            {"backup_script_template_creation_result": self.create_script(name=script_name,
                                                                          script_content=cli_command, target=1)})
        result.append({"backup_script_execution_result": self.run_script_on_single_device(script_name=script_name,
                                                                                          device_name=device_name,
                                                                                          vdom=vdom
                                                                                          ),
                       "device": device_name, "vdom": vdom})
        return result
