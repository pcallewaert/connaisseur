import json
from jsonschema import validate, ValidationError
from connaisseur.workload_object import WorkloadObject
from connaisseur.exceptions import InvalidFormatException


class AdmissionRequest:
    SCHEMA_PATH = "/app/connaisseur/res/ad_request_schema.json"

    def __init__(self, ad_request: dict):
        self.__validate(ad_request)

        request = ad_request["request"]
        self.uid = request["uid"]
        self.kind = request["kind"]["kind"]
        self.namespace = request["namespace"]
        self.operation = request["operation"]
        self.user = request["userInfo"]["username"]
        self.wl_object = WorkloadObject(request["object"], self.namespace)

    def __validate(self, request: dict):
        with open(self.SCHEMA_PATH, "r") as schemafile:
            schema = json.load(schemafile)

        try:
            validate(instance=request, schema=schema)
        except ValidationError as err:
            msg = "{validation_kind} has an invalid format: {validation_err}."
            raise InvalidFormatException(
                message=msg,
                validation_kind="AdmissionRequest",
                validation_err=str(err),
                request=request,
            ) from err

    @property
    def context(self):
        return {
            "user": self.user,
            "operation": self.operation,
            "kind": self.kind,
            "name": self.wl_object.name,
            "namespace": self.namespace,
        }
