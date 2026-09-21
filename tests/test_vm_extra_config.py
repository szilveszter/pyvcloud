# VMware vCloud Director Python SDK
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from unittest.mock import Mock

from lxml import etree
from lxml import objectify

from pyvcloud.vcd.client import Client
from pyvcloud.vcd.client import EntityType
from pyvcloud.vcd.client import NSMAP
from pyvcloud.vcd.exceptions import InvalidStateException
from pyvcloud.vcd.vm import VM


class TestVmExtraConfig(unittest.TestCase):

    def setUp(self):
        self.resource = objectify.fromstring('''
            <Vm xmlns="http://www.vmware.com/vcloud/v1.5"
                xmlns:ovf="http://schemas.dmtf.org/ovf/envelope/1"
                xmlns:vmw="http://www.vmware.com/schema/ovf"
                href="https://vcd.example.com/api/vApp/vm-123">
                <Link rel="reconfigureVm"
                    type="application/vnd.vmware.vcloud.vm+xml"
                    href="https://vcd.example.com/api/vApp/vm-123/action/reconfigureVm"/>
                <Description>Keep this description</Description>
                <ovf:VirtualHardwareSection>
                    <ovf:Info>Virtual hardware requirements</ovf:Info>
                    <ovf:System/>
                    <ovf:Item/>
                    <vmw:Config vmw:key="firmware" vmw:value="efi"/>
                </ovf:VirtualHardwareSection>
            </Vm>''')
        self.hardware = self.resource.find('ovf:VirtualHardwareSection', NSMAP)
        self.client = Mock(spec=Client)
        self.vm = VM(self.client, resource=self.resource)

    def assert_posted(self, task):
        self.client.post_resource.assert_called_once_with(
            self.vm.href + '/action/reconfigureVm',
            self.resource, EntityType.VM.value)
        self.assertIs(task, self.client.post_resource.return_value)

    def assert_extra_config(self, element, key, value, required):
        self.assertEqual(element.tag, '{%s}ExtraConfig' % NSMAP['vmw'])
        self.assertEqual(dict(element.attrib), {
            '{%s}key' % NSMAP['vmw']: key,
            '{%s}value' % NSMAP['vmw']: value,
            '{%s}required' % NSMAP['ovf']: required,
        })

    def test_adds_first_extra_config_and_preserves_vm_contents(self):
        children_before = [etree.tostring(child)
                           for child in self.hardware.iterchildren()]
        task = self.vm.add_extra_config_element('guestinfo.hostname', 'host1')

        self.assert_posted(task)
        elements = self.vm.get_vm_extra_config_elements()
        self.assertEqual(len(elements), 1)
        self.assertIs(elements[0].getparent(), self.hardware)
        self.assert_extra_config(elements[0], 'guestinfo.hostname', 'host1',
                                 'false')
        children_after = list(self.hardware.iterchildren())
        self.assertEqual(
            [etree.tostring(child) for child in children_after[:-1]],
            children_before)
        self.assertEqual(self.resource.Description.text,
                         'Keep this description')

    def test_preserves_existing_extra_config(self):
        existing = []
        for key, value in (('guestinfo.one', 'one'), ('guestinfo.two', 'two')):
            element = etree.SubElement(self.hardware,
                                       '{%s}ExtraConfig' % NSMAP['vmw'])
            element.set('{%s}key' % NSMAP['vmw'], key)
            element.set('{%s}value' % NSMAP['vmw'], value)
            element.set('{%s}required' % NSMAP['ovf'], 'true')
            existing.append(element)
        before = [etree.tostring(element) for element in existing]

        task = self.vm.add_extra_config_element('guestinfo.three', 'three')

        self.assert_posted(task)
        self.assertEqual(self.vm.list_vm_extra_config_info(), {
            'guestinfo.one': 'one',
            'guestinfo.two': 'two',
            'guestinfo.three': 'three',
        })
        self.assertEqual([etree.tostring(element) for element in existing],
                         before)

    def test_serializes_required_and_xml_special_characters(self):
        key = 'guestinfo.a&b'
        value = '<config value="a&b">café</config>'
        task = self.vm.add_extra_config_element(key, value, required=True)

        self.assert_posted(task)
        parsed = objectify.fromstring(etree.tostring(self.resource))
        element = parsed.find('ovf:VirtualHardwareSection/vmw:ExtraConfig',
                              NSMAP)
        self.assert_extra_config(element, key, value, 'true')

    def test_adds_to_empty_hardware_section(self):
        self.hardware.clear()
        task = self.vm.add_extra_config_element('guestinfo.empty', '')

        self.assert_posted(task)
        self.assertEqual(self.vm.list_vm_extra_config_info(),
                         {'guestinfo.empty': ''})

    def test_fetches_vm_when_initialized_with_href(self):
        self.client.get_resource.return_value = self.resource
        self.vm = VM(self.client, href=self.resource.get('href'))

        task = self.vm.add_extra_config_element('guestinfo.hostname', 'host1')

        self.client.get_resource.assert_called_once_with(self.vm.href)
        self.assert_posted(task)
        self.assertEqual(self.vm.list_vm_extra_config_info(),
                         {'guestinfo.hostname': 'host1'})

    def test_missing_hardware_section_raises_before_posting(self):
        self.resource.remove(self.hardware)
        before = etree.tostring(self.resource)

        with self.assertRaisesRegex(InvalidStateException,
                                    'VirtualHardwareSection'):
            self.vm.add_extra_config_element('guestinfo.hostname', 'host1')

        self.client.post_resource.assert_not_called()
        self.assertEqual(etree.tostring(self.resource), before)


if __name__ == '__main__':
    unittest.main()
