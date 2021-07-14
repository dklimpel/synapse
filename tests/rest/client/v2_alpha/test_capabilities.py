# Copyright 2019 New Vector Ltd
#
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
import synapse.rest.admin
from synapse.api.room_versions import KNOWN_ROOM_VERSIONS
from synapse.rest.client.v1 import login
from synapse.rest.client.v2_alpha import capabilities

from tests import unittest
from tests.unittest import override_config


class CapabilitiesTestCase(unittest.HomeserverTestCase):

    servlets = [
        synapse.rest.admin.register_servlets_for_client_rest_resource,
        capabilities.register_servlets,
        login.register_servlets,
    ]

    def make_homeserver(self, reactor, clock):
        self.url = b"/_matrix/client/r0/capabilities"
        hs = self.setup_test_homeserver()
        self.config = hs.config
        self.auth_handler = hs.get_auth_handler()
        return hs

    def prepare(self, reactor, clock, hs):
        self.localpart = "user"
        self.password = "pass"
        self.user = self.register_user(self.localpart, self.password)

    def test_check_auth_required(self):
        channel = self.make_request("GET", self.url)

        self.assertEqual(channel.code, 401)

    def test_get_room_version_capabilities(self):
        access_token = self.login(self.localpart, self.password)

        channel = self.make_request("GET", self.url, access_token=access_token)
        capabilities = channel.json_body["capabilities"]

        self.assertEqual(channel.code, 200)
        for room_version in capabilities["m.room_versions"]["available"].keys():
            self.assertTrue(room_version in KNOWN_ROOM_VERSIONS, "" + room_version)

        self.assertEqual(
            self.config.default_room_version.identifier,
            capabilities["m.room_versions"]["default"],
        )

    def test_get_change_password_capabilities_password_login(self):
        access_token = self.login(self.localpart, self.password)

        self._test_capability("m.change_password", access_token, True)

    @override_config({"password_config": {"localdb_enabled": False}})
    def test_get_change_password_capabilities_localdb_disabled(self):
        access_token = self.get_success(
            self.auth_handler.get_access_token_for_user_id(
                self.user, device_id=None, valid_until_ms=None
            )
        )

        self._test_capability("m.change_password", access_token, False)

    @override_config({"password_config": {"enabled": False}})
    def test_get_change_password_capabilities_password_disabled(self):
        access_token = self.get_success(
            self.auth_handler.get_access_token_for_user_id(
                self.user, device_id=None, valid_until_ms=None
            )
        )

        self._test_capability("m.change_password", access_token, False)

    def test_get_change_users_attributes_capabilities(self):
        """
        Test that per default server returns `m.change_password`
        but not `org.matrix.msc3283.enable_set_displayname`.
        In feature we can add further capabilites.
        If MSC3283 is in spec, the test must be updated to test that server reponds
        with `m.enable_set_displayname` per default.
        """
        access_token = self.login(self.localpart, self.password)

        channel = self.make_request("GET", self.url, access_token=access_token)
        capabilities = channel.json_body["capabilities"]

        self.assertEqual(channel.code, 200)
        self.assertTrue(capabilities["m.change_password"]["enabled"])
        self.assertNotIn("org.matrix.msc3283.enable_set_displayname", capabilities)

    @override_config({"enable_set_displayname": False})
    def test_get_change_displayname_capabilities_displayname_disabled(self):
        """
        Test if change displayname is disabled that the server responds it.
        """
        access_token = self.login(self.localpart, self.password)

        self._test_capability(
            "org.matrix.msc3283.enable_set_displayname", access_token, False
        )

    def _test_capability(self, capability: str, access_token: str, expect_success=True):
        """
        Requests the capabilities from server and check if the value is expected.
        """
        channel = self.make_request("GET", self.url, access_token=access_token)
        capabilities = channel.json_body["capabilities"]

        self.assertEqual(channel.code, 200)

        if expect_success:
            self.assertTrue(capabilities[capability]["enabled"])
        else:
            self.assertFalse(capabilities[capability]["enabled"])
