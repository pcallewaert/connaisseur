import os
import collections
import json
import yaml
from jsonschema import validate, ValidationError
from connaisseur.exceptions import (
    NotFoundException,
    InvalidConfigurationFormatError,
)
from connaisseur.validators.validator import Validator
from connaisseur.util import safe_path_func


class Config:
    """
    Config Object, that contains all notary configurations inside a list.
    """

    path = "/app/connaisseur-config/config.yaml"
    secrets_path = "/app/connaisseur-config/config-secrets.yaml"
    external_path = "/app/connaisseur-config/"
    schema_path = "/app/connaisseur/res/config_schema.json"
    validators: list = []

    def __init__(self):
        """
        Creates a Config object, containing all validator configurations. It does so by
        reading a config file, doing input validation and then creating Validator objects,
        storing them in a list.

        Raises `NotFoundException` if the configuration file is not found.

        Raises `InvalidFormatException` if the configuration file has an invalid format.
        """
        with open(self.path, "r") as configfile:
            config_content = yaml.safe_load(configfile)

        with open(self.secrets_path, "r") as secrets_configfile:
            secrets_config_content = yaml.safe_load(secrets_configfile)

        config = self.__merge_configs(config_content, secrets_config_content)

        self.__validate(config)

        self.validators = [Validator(**validator) for validator in config]

    def __merge_configs(self, config: dict, secrets_config: dict):
        if not config:
            msg = "Error loading connaisseur config file."
            raise NotFoundException(message=msg)

        for validator in config:
            validator.update(secrets_config.get(validator.get("name"), {}))
            auth_path = f'{self.external_path}{validator["name"]}/auth.yaml'
            if safe_path_func(os.path.exists, self.external_path, auth_path):
                with safe_path_func(
                    open, self.external_path, auth_path, "r"
                ) as auth_file:
                    auth_dict = {"auth": yaml.safe_load(auth_file)}
                validator.update(auth_dict)
        return config

    def __validate(self, config: dict):
        with open(self.schema_path, "r") as schema_file:
            schema = json.load(schema_file)

        try:
            validate(instance=config, schema=schema)
            validator_names = [validator.get("name") for validator in config]
            if collections.Counter(validator_names)["default"] > 1:
                msg = "Too many default validator configurations."
                raise InvalidConfigurationFormatError(message=msg)

            # for validator in config:
            #     key_names = [key.get("name") for key in validator.get("root_keys")]
            #     if collections.Counter(key_names)["default"] > 1:
            #         msg = (
            #             "Too many default keys in validator "
            #             "configuration {validator_name}."
            #         )
            #         raise InvalidConfigurationFormatError(
            #             message=msg, validator_name=validator.get("name")
            #         )
        except ValidationError as err:
            msg = "{validation_kind} has an invalid format: {validation_err}."
            raise InvalidConfigurationFormatError(
                message=msg,
                validation_kind="Connaisseur configuration",
                validation_err=str(err),
            ) from err

    def get_validator(self, validator_name: str = None):
        """
        Returns the validator configuration with the given `validator_name`. If
        `validator_name` is None, the element with `name=default` is taken, or the only
        existing element.

        Raises `NotFoundException` if no matching or default element can be found.
        """
        try:
            if len(self.validators) < 2:
                return next(iter(self.validators))

            validator_name = validator_name or "default"
            return next(
                validator
                for validator in self.validators
                if validator.name == validator_name
            )
        except StopIteration as err:
            if len(self.validators) < 2:
                msg = "No validator configurations could be found."
            else:
                msg = "Unable to find validator configuration {validator_name}."
            raise NotFoundException(message=msg, validator_name=validator_name) from err
