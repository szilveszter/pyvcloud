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

import logging
import unittest
from unittest.mock import Mock
from unittest.mock import patch

import requests
from urllib3._collections import HTTPHeaderDict

from pyvcloud.vcd.client import API_CURRENT_VERSIONS
from pyvcloud.vcd.client import ApiVersion
from pyvcloud.vcd.client import BasicLoginCredentials
from pyvcloud.vcd.client import Client
from pyvcloud.vcd.client import VCD_API_CURRENT_VERSIONS
from pyvcloud.vcd.client import VcdApiVersionObj
from pyvcloud.vcd.exceptions import VcdException
from pyvcloud.vcd.vcd_api_version import VCDApiVersion
from pyvcloud.vcd.vcd_client import VcdClient


def response(content, headers=None, status=200):
    result = requests.Response()
    result.status_code = status
    result._content = content.encode('utf-8')
    result.headers.update(headers or {})
    return result


def versions_response(*versions):
    entries = ''.join('<VersionInfo><Version>{}</Version></VersionInfo>'
                      .format(version) for version in versions)
    return response('<SupportedVersions xmlns="http://www.vmware.com/vcloud/'
                    'versions">{}</SupportedVersions>'.format(entries))


class TestApiVersions(unittest.TestCase):

    def setUp(self):
        # Keep all tests offline and avoid creating log files.
        logger_patch = patch.object(Client, '_get_default_logger')
        logger_patch.start()
        self.addCleanup(logger_patch.stop)
        request_patch = patch.object(requests.Session, 'request',
                                     autospec=True)
        self.request = request_patch.start()
        self.addCleanup(request_patch.stop)
        self.request.side_effect = AssertionError('Unexpected HTTP request')

    def client(self, client_class=Client, api_version=None):
        client = client_class('https://vcd.example.com',
                              api_version=api_version)
        client._logger = logging.getLogger(__name__)
        self.addCleanup(lambda: client._session.close()
                        if client._session is not None else None)
        return client

    def serve_versions(self, *versions):
        self.request.side_effect = None
        self.request.return_value = versions_response(*versions)

    def test_supported_version_registries(self):
        for name, version in (('VERSION_37', '37.0'),
                              ('VERSION_37_1', '37.1'),
                              ('VERSION_37_2', '37.2')):
            with self.subTest(version=version):
                self.assertEqual(getattr(ApiVersion, name).value, version)
                self.assertEqual(getattr(VcdApiVersionObj, name).value,
                                 VCDApiVersion(version))
                self.assertIn(version, API_CURRENT_VERSIONS)
                self.assertIn(VCDApiVersion(version), VCD_API_CURRENT_VERSIONS)
        self.assertEqual(API_CURRENT_VERSIONS[-1], '37.2')
        self.assertEqual(VCD_API_CURRENT_VERSIONS[-1], VCDApiVersion('37.2'))
        self.assertEqual(API_CURRENT_VERSIONS,
                         sorted(API_CURRENT_VERSIONS, key=VCDApiVersion))
        self.assertEqual(VCD_API_CURRENT_VERSIONS,
                         sorted(VCD_API_CURRENT_VERSIONS))

    def test_negotiates_highest_mutually_supported_version(self):
        for client_class in (Client, VcdClient):
            for versions, expected in (
                    (('37.2',), '37.2'),
                    (('38.0', '36.0', '37.2', '37.1', '37.0'), '37.2'),
                    (('36.0', '37.1'), '37.1'),
                    (('36.0', '37.0'), '37.0'),
                    (('29.0', '35.0', '36.0'), '36.0'),
                    (('29.0',), '29.0')):
                with self.subTest(client=client_class.__name__,
                                  versions=versions):
                    client = self.client(client_class)
                    self.serve_versions(*versions)
                    client._negotiate_api_version()
                    self.assertEqual(client.get_api_version(), expected)
                    self.assertEqual(client.get_vcd_api_version(),
                                     VCDApiVersion(expected))

    def test_explicit_version_is_preserved_without_discovery(self):
        for client_class in (Client, VcdClient):
            with self.subTest(client=client_class.__name__):
                client = self.client(client_class, api_version='37.2')
                client._negotiate_api_version()
                self.assertEqual(client.get_api_version(), '37.2')
                self.assertEqual(client.get_vcd_api_version(),
                                 VCDApiVersion('37.2'))
        self.request.assert_not_called()

    def test_no_common_version_raises(self):
        self.serve_versions('28.0', '38.0')
        with self.assertRaisesRegex(VcdException, 'supported API version'):
            self.client()._negotiate_api_version()

    def test_discovery_filters_deprecated_versions_and_sorts_numerically(self):
        self.request.side_effect = None
        self.request.return_value = response('''
            <SupportedVersions xmlns="http://www.vmware.com/vcloud/versions">
                <VersionInfo deprecated="false">
                    <Version>37.10</Version>
                </VersionInfo>
                <VersionInfo deprecated="true">
                    <Version>38.0</Version>
                </VersionInfo>
                <VersionInfo><Version>37.0</Version></VersionInfo>
                <VersionInfo deprecated="FALSE">
                    <Version>37.2</Version>
                </VersionInfo>
                <VersionInfo deprecated="TRUE">
                    <Version>37.1</Version>
                </VersionInfo>
                <AlphaVersion deprecated="false">
                    <Version>39.0.0-alpha-1234</Version>
                </AlphaVersion>
                <AlphaVersion deprecated="true">
                    <Version>40.0.0-alpha-5678</Version>
                </AlphaVersion>
            </SupportedVersions>''')
        client = self.client()
        self.assertEqual(client.get_supported_versions_list(),
                         ['37.0', '37.2', '37.10'])
        self.assertEqual(client.get_supported_versions_list(
            include_alpha_versions=True),
            ['37.0', '37.2', '37.10', '39.0.0-alpha'])
        self.assertEqual(client.get_supported_versions(),
                         [VCDApiVersion(v) for v in ('37.0', '37.2', '37.10')])

    def test_negotiation_skips_deprecated_and_alpha_versions(self):
        self.request.side_effect = None
        self.request.return_value = response('''
            <SupportedVersions>
                <VersionInfo><Version>36.0</Version></VersionInfo>
                <VersionInfo deprecated="true">
                    <Version>37.2</Version>
                </VersionInfo>
                <AlphaVersion>
                    <Version>37.0.0-alpha-1234</Version>
                </AlphaVersion>
            </SupportedVersions>''')
        client = self.client()
        client._negotiate_api_version()
        self.assertEqual(client.get_api_version(), '36.0')

    def test_all_versions_deprecated_raises(self):
        self.request.side_effect = None
        self.request.return_value = response('''
            <SupportedVersions>
                <VersionInfo deprecated="true">
                    <Version>37.2</Version>
                </VersionInfo>
            </SupportedVersions>''')
        with self.assertRaisesRegex(VcdException, 'supported API version'):
            self.client()._negotiate_api_version()

    def test_highest_server_version_updates_both_representations(self):
        self.serve_versions('36.0', '37.0', '37.1', '37.2')
        client = self.client(api_version='36.0')
        self.assertEqual(client.set_highest_supported_version(), '37.2')
        self.assertEqual(client.get_vcd_api_version(), VCDApiVersion('37.2'))

    def test_login_and_xml_requests_use_37_2(self):
        for client_class in (Client, VcdClient):
            for org in ('tenant', 'System'):
                with self.subTest(client=client_class.__name__, org=org):
                    self.request.reset_mock()
                    self.request.side_effect = [
                        versions_response('36.0', '37.2'),
                        response('{}',
                                 {'X-VMWARE-VCLOUD-ACCESS-TOKEN': 'jwt'}),
                        response('<Session org="{}"/>'.format(org)),
                        response('<Org name="tenant"/>'),
                    ]
                    client = self.client(client_class)
                    client.set_credentials(
                        BasicLoginCredentials('user', org, 'password'))
                    result = client.get_resource(
                        'https://vcd.example.com/api/org/123')
                    self.assertEqual(result.get('name'), 'tenant')
                    self.assertEqual(client.is_sysadmin(), org == 'System')
                    discovery, login, session, resource = \
                        self.request.call_args_list
                    self.assertEqual(discovery[1]['headers']['Accept'],
                                     'application/*+xml')
                    endpoint = client.get_cloudapi_uri() + '/1.0.0/sessions'
                    if org == 'System':
                        endpoint += '/provider'
                    self.assertEqual(login[0][1:], ('POST', endpoint))
                    self.assertEqual(login[1]['auth'],
                                     ('user@' + org, 'password'))
                    self.assertEqual(login[1]['headers']['Accept'],
                                     'application/json;version=37.2')
                    for call in (session, resource):
                        self.assertEqual(call[1]['headers']['Accept'],
                                         'application/*+xml;version=37.2')
                        self.assertEqual(call[0][0].headers['Authorization'],
                                         'Bearer jwt')

    def test_openapi_requests_use_37_2(self):
        self.request.side_effect = [
            response('{}', {'X-VMWARE-VCLOUD-ACCESS-TOKEN': 'jwt'}),
            response('<Session org="tenant"/>'),
        ]
        client = self.client(VcdClient, api_version='37.2')
        client.set_credentials(
            BasicLoginCredentials('user', 'tenant', 'password'))
        rest_response = Mock(status=200, data=b'{}')
        rest_response.getheaders.return_value = HTTPHeaderDict()
        with patch.object(client.rest_client, 'GET',
                          return_value=rest_response) as get:
            client.call_api('/1.0.0/orgs', 'GET')
        self.assertEqual(get.call_args[0][0],
                         'https://vcd.example.com/cloudapi/1.0.0/orgs')
        self.assertEqual(get.call_args[1]['headers']['Accept'],
                         'application/json;version=37.2')
        self.assertEqual(get.call_args[1]['headers']['Authorization'],
                         'Bearer jwt')
        self.assertEqual(client.get_last_status(), 200)


if __name__ == '__main__':
    unittest.main()
