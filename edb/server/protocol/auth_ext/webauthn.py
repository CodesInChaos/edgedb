#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2024-present MagicStack Inc. and the EdgeDB authors.
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
#

import dataclasses
import base64
import json
import webauthn

from typing import Any, Optional

from edb.errors import ConstraintViolationError
from edb.server.protocol import execute

from . import config, data, errors, util, local


@dataclasses.dataclass(repr=False)
class WebAuthnRegistrationChallenge:
    """
    Object that represents the ext::auth::WebAuthnRegistrationChallenge type
    """

    id: str
    challenge: bytes
    user_handle: bytes
    email: str


class Client(local.Client):
    def __init__(self, db: Any):
        self.db = db
        self.provider = self._get_provider()
        self.app_name = self._get_app_name()

    def _get_provider(self) -> config.WebAuthnProvider:
        provider_name = "builtin::local_webauthn"
        provider_client_config = util.get_config(
            self.db, "ext::auth::AuthConfig::providers", frozenset
        )
        for cfg in provider_client_config:
            if cfg.name == provider_name:
                return config.WebAuthnProvider(
                    name=cfg.name,
                    relying_party_origin=cfg.relying_party_origin,
                    require_verification=cfg.require_verification,
                )

        raise errors.MissingConfiguration(
            provider_name, f"Provider is not configured"
        )

    def _get_app_name(self) -> Optional[str]:
        return util.maybe_get_config(self.db, "ext::auth::AuthConfig::app_name")

    async def create_registration_options_for_email(self, email: str):
        registration_options = webauthn.generate_registration_options(
            rp_id=self.provider.relying_party_id,
            rp_name=(self.app_name or self.provider.relying_party_origin),
            user_name=email,
            user_display_name=email,
        )

        await self._create_registration_challenge(
            email=email,
            challenge=registration_options.challenge,
            user_handle=registration_options.user.id,
        )

        return (
            base64.urlsafe_b64encode(registration_options.user.id).decode(),
            webauthn.options_to_json(registration_options).encode(),
        )

    async def _create_registration_challenge(
        self,
        email: str,
        challenge: bytes,
        user_handle: bytes,
    ):
        await execute.parse_execute_json(
            self.db,
            """
with
    challenge := <bytes>$challenge,
    user_handle := <bytes>$user_handle,
    email := <str>$email,
insert ext::auth::WebAuthnRegistrationChallenge {
    challenge := challenge,
    user_handle := user_handle,
    email := email,
}""",
            variables={
                "challenge": challenge,
                "user_handle": user_handle,
                "email": email,
            },
            cached_globally=True,
        )

    async def register(
        self,
        credentials: str,
        email: str,
        user_handle: bytes,
    ):
        registration_challenge = await self._get_registration_challenge(
            email=email,
            user_handle=user_handle,
        )
        await self._delete_registration_challenges(
            email=email,
            user_handle=user_handle,
        )

        registration_verification = webauthn.verify_registration_response(
            credential=credentials,
            expected_challenge=registration_challenge.challenge,
            expected_rp_id=self.provider.relying_party_id,
            expected_origin=self.provider.relying_party_origin,
        )

        try:
            result = await execute.parse_execute_json(
                self.db,
                """
with
    email := <str>$email,
    user_handle := <bytes>$user_handle,
    credential_id := <bytes>$credential_id,
    public_key := <bytes>$public_key,
    identity := (insert ext::auth::LocalIdentity {
        issuer := "local",
        subject := "",
    }),
    factor := (insert ext::auth::WebAuthnFactor {
        email := email,
        user_handle := user_handle,
        credential_id := credential_id,
        public_key := public_key,
        identity := identity,
    }),
select identity { * };""",
                variables={
                    "email": email,
                    "user_handle": user_handle,
                    "credential_id": registration_verification.credential_id,
                    "public_key": (
                        registration_verification.credential_public_key
                    ),
                },
                cached_globally=True,
            )
        except Exception as e:
            exc = await execute.interpret_error(e, self.db)
            if isinstance(exc, ConstraintViolationError):
                raise errors.UserAlreadyRegistered()
            else:
                raise exc

        result_json = json.loads(result.decode())
        assert len(result_json) == 1

        return data.LocalIdentity(**result_json[0])

    async def _get_registration_challenge(
        self,
        email: str,
        user_handle: bytes,
    ) -> WebAuthnRegistrationChallenge:
        result = await execute.parse_execute_json(
            self.db,
            """
with
    email := <str>$email,
    user_handle := <bytes>$user_handle,
select ext::auth::WebAuthnRegistrationChallenge {
    id,
    challenge,
    user_handle,
    email,
}
filter .email = email and .user_handle = user_handle;""",
            variables={
                "email": email,
                "user_handle": user_handle,
            },
            cached_globally=True,
        )
        result_json = json.loads(result.decode())
        assert len(result_json) == 1
        challenge_dict = result_json[0]

        return WebAuthnRegistrationChallenge(
            id=challenge_dict["id"],
            challenge=base64.b64decode(challenge_dict["challenge"]),
            user_handle=base64.b64decode(challenge_dict["user_handle"]),
            email=challenge_dict["email"],
        )

    async def _delete_registration_challenges(
        self,
        email: str,
        user_handle: bytes,
    ):
        await execute.parse_execute_json(
            self.db,
            """
with
    email := <str>$email,
    user_handle := <bytes>$user_handle,
delete ext::auth::WebAuthnRegistrationChallenge
filter .email = email and .user_handle = user_handle;""",
            variables={
                "email": email,
                "user_handle": user_handle,
            },
        )
