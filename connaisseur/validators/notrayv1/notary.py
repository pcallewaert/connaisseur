import os
import re
from urllib.parse import quote, urlencode
import requests
import yaml
from connaisseur.image import Image
from connaisseur.validators.notrayv1.tuf_role import TUFRole
from connaisseur.validators.notrayv1.trust_data import TrustData
from connaisseur.exceptions import (
    UnreachableError,
    NotFoundException,
    InvalidFormatException,
    UnknownTypeException,
    PathTraversalError,
)
from connaisseur.util import safe_path_func


class Notary:

    name: str
    host: str
    pub_root_keys: list
    is_acr: bool
    is_cosign: bool
    auth: dict
    selfsigned_cert: str

    SELFSIGNED_PATH = "/app/connaisseur/certs/{}.crt"

    def __init__(self, name: str, host: str, pub_root_keys: list, **kwargs):
        """
        Creates a Notary object from a dictionary.

        Raises `InvalidFormatException` should the mandatory fields be missing.
        """

        if not (name and host and pub_root_keys):
            msg = "{validation_kind} {notary_name} has an invalid format."
            raise InvalidFormatException(
                message=msg,
                validation_kind="Notary configuration",
                notary_name=name,
                notary_host=host,
                notary_keys=pub_root_keys,
            )

        self.name = name
        self.host = host
        self.pub_root_keys = pub_root_keys
        self.is_acr = kwargs.get("is_acr", False)
        self.is_cosign = kwargs.get("is_cosign", False)
        self.auth = kwargs.get("auth", {})
        self.selfsigned_cert = self.__create_selfsigned_cert(kwargs.get("cert"))

    def __create_selfsigned_cert(self, cert: str):
        if not cert:
            return None

        cert_path = self.SELFSIGNED_PATH.format(self.name)

        if not safe_path_func(os.path.exists, "/app/connaisseur/certs", cert_path):
            safe_path_func(
                os.makedirs,
                "/app/connaisseur/certs",
                os.path.dirname(cert_path),
                exist_ok=True,
            )
            with safe_path_func(open, "/app/connaisseur/certs", cert_path, "w") as file:
                file.write(cert)

        return cert_path

    def get_key(self, key_name: str = None):
        """
        Returns the public root key with name `key_name` in DER format, without any
        whitespaces. If `key_name` is None, the top most element of the public root key
        list is returned.

        Raises `NotFoundException` if no top most element can be found.
        """

        try:
            if len(self.pub_root_keys) < 2:
                key = next(iter(self.pub_root_keys))["key"]
            else:
                key_name = key_name or "default"
                key = next(
                    key["key"] for key in self.pub_root_keys if key["name"] == key_name
                )
            return "".join(key)
        except StopIteration as err:
            if len(self.pub_root_keys) < 2:
                msg = "Not public keys could be found."
            else:
                msg = "Key {key_name} could not be found."
            raise NotFoundException(
                message=msg, key_name=key_name, notary_name=self.name
            ) from err

    @property
    def healthy(self):
        if self.is_acr:
            return True

        try:
            url = f"https://{self.host}/_notary_server/health"
            request_kwargs = {"url": url, "verify": self.selfsigned_cert}
            response = requests.get(**request_kwargs)

            return response.status_code == 200
        except Exception:
            return False

    def get_trust_data(self, image: Image, role: TUFRole, token: str = None):
        if not self.healthy:
            msg = "Unable to reach notary host {notary_name}."
            raise UnreachableError(
                message=msg, notary_name=self.name, tuf_role=(str(role))
            )

        im_repo = f"{image.repository}/" if image.repository else ""
        url = (
            f"https://{self.host}/v2/{image.registry}/{im_repo}"
            f"{image.name}/_trust/tuf/{str(role)}.json"
        )

        request_kwargs = {
            "url": url,
            "verify": self.selfsigned_cert,
            "headers": ({"Authorization": f"Bearer {token}"} if token else None),
        }

        response = requests.get(**request_kwargs)

        if (
            response.status_code == 401
            and not token
            and ("www-authenticate" in [k.lower() for k in response.headers])
        ):
            auth_url = self.__parse_auth(
                {k.lower(): v for k, v in response.headers.items()}["www-authenticate"]
            )
            token = self.__get_auth_token(auth_url)
            return self.get_trust_data(image, role, token)

        if response.status_code == 404:
            msg = "Unable to get {tuf_role} trust data from {notary_name}."
            raise NotFoundException(
                message=msg, notary_name=self.name, tuf_role=str(role)
            )

        response.raise_for_status()

        return TrustData(response.json(), str(role))

    def get_delegation_trust_data(self, image: Image, role: TUFRole, token: str = None):
        try:
            return self.get_trust_data(image, role, token)
        except Exception as ex:
            if os.environ.get("LOG_LEVEL", "INFO") == "DEBUG":
                raise ex
            return None

    def __parse_auth(self, header: str):
        """
        Generates an URL from the 'Www-authenticate' header, where a token can be
        requested.
        """
        auth_types = [
            "Basic",
            "Bearer",
            "Digest",
            "HOBA",
            "Mutual",
            "Negotiate",
            "OAuth",
            "SCRAM-SHA-1",
            "SCRAM-SHA-256",
            "vapid",
        ]
        auth_type_re = re.compile("({}) realm".format("|".join(auth_types)))
        params_re = re.compile(r'(\w+)="?([\w\.\/\:\-\_]+)"?')

        auth_type = next(iter(auth_type_re.findall(header)), None)
        params_dict = dict(params_re.findall(header))

        if not auth_type or auth_type != "Bearer":
            msg = (
                "{auth_type} is an unsupported authentication"
                " type in notary {notary_name}."
            )
            raise UnknownTypeException(
                message=msg, auth_type=auth_type, notary_name=self.name
            )

        try:
            realm = quote(params_dict.pop("realm"), safe="/:")
        except KeyError as err:
            msg = (
                "Unable to find authentication realm in auth"
                " header for notary {notary_name}."
            )
            raise NotFoundException(
                message=msg, notary_name=self.name, auth_header=params_dict
            ) from err
        params = urlencode(params_dict, safe="/:")

        url = f"{realm}?{params}"

        if not url.startswith("https"):
            msg = (
                "authentication through insecure channel "
                "for notary {notary_name} is prohibited."
            )
            raise InvalidFormatException(
                message=msg, notary_name=self.name, auth_url=url
            )

        if ".." in url or url.count("//") > 1:
            msg = (
                "Potential path traversal in authentication"
                " url for notary {notary_name}."
            )
            raise PathTraversalError(message=msg, notary_name=self.name, auth_url=url)

        return url

    def __get_auth_token(self, url: str):
        """
        Return the JWT from the given `url`, using user and password from
        environment variables.

        Raises an exception if a HTTP error status code occurs.
        """
        request_kwargs = {
            "url": url,
            "verify": self.selfsigned_cert,
            "auth": (requests.auth.HTTPBasicAuth(*self.auth) if self.auth else None),
        }

        response = requests.get(**request_kwargs)

        if response.status_code >= 500:
            msg = "Unable to get authentication token form {auth_url}."
            raise NotFoundException(message=msg, notary_name=self.name, auth_url=url)

        response.raise_for_status()

        try:
            token_key = "access_token" if self.is_acr else "token"
            token = response.json()[token_key]
        except KeyError as err:
            msg = "Unable to retrieve authentication token from {auth_url} response."
            raise NotFoundException(
                message=msg, notary_name=self.name, auth_url=url
            ) from err

        token_re = r"^[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*$"  # nosec

        if not re.match(token_re, token):
            msg = "{validation_kind} has an invalid format."
            raise InvalidFormatException(
                message=msg,
                validation_kind="Authentication token",
                notary_name=self.name,
                auth_url=url,
            )
        return token
