import connaisseur.kube_api as k_api
from connaisseur.container import Container
from connaisseur.exceptions import UnknownAPIVersionError, ParentNotFoundError


SUPPORTED_API_VERSIONS = {
    "Pod": ["v1"],
    "Deployment": ["apps/v1", "apps/v1beta1", "apps/v1beta2"],
    "ReplicationController": ["v1"],
    "ReplicaSet": ["apps/v1", "apps/v1beta1", "apps/v1beta2"],
    "DaemonSet": ["apps/v1", "apps/v1beta1", "apps/v1beta2"],
    "StatefulSet": ["apps/v1", "apps/v1beta1", "apps/v1beta2"],
    "Job": ["batch/v1"],
    "CronJob": ["batch/v1beta1", "batch/v2alpha1"],
}


class WorkloadObject:
    container_path = "/spec/template/spec/{container_type}/{index}/image"

    def __new__(
        cls, request_object: dict, namespace: str
    ):  # pylint: disable=unused-argument
        if request_object["kind"] == "Pod":
            return super(WorkloadObject, cls).__new__(Pod)
        elif request_object["kind"] == "CronJob":
            return super(WorkloadObject, cls).__new__(CronJob)
        return super(WorkloadObject, cls).__new__(WorkloadObject)

    def __init__(self, request_object: dict, namespace: str):
        self.kind = request_object["kind"]
        self.api_version = request_object["apiVersion"]
        self.namespace = namespace
        self.name = request_object["metadata"].get("name") or request_object[
            "metadata"
        ].get("generateName")
        self._spec = request_object["spec"]
        self._owner = request_object["metadata"].get("ownerReferences", [])

        if self.api_version not in SUPPORTED_API_VERSIONS[self.kind]:
            msg = (
                "{wl_obj_version} is not in the supported API version list "
                "for {wl_obj_kind} {wl_obj_name}."
            )
            raise UnknownAPIVersionError(
                message=msg,
                wl_obj_version=self.api_version,
                wl_obj_kind=self.kind,
                wl_obj_name=self.name,
            )

    @property
    def parent_containers(self):
        parent_containers = []
        for owner in self._owner:
            api_version = owner["apiVersion"]
            kind = owner["kind"].lower() + "s"
            name = owner["name"]
            uid = owner["uid"]

            parent = k_api.request_kube_api(
                f"apis/{api_version}/namespaces/{self.namespace}/{kind}/{name}"
            )

            if parent["metadata"]["uid"] != uid:
                msg = (
                    "Couldn't find the right parent"
                    " resource {parent_kind} {parent_name}."
                )
                raise ParentNotFoundError(
                    message=msg, parent_kind=kind, parent_name=name, parent_uid=uid
                )

            parent_containers += WorkloadObject(parent, self.namespace).containers
        return parent_containers

    @property
    def containers(self):
        spec = self._spec["template"]["spec"]
        container_list = [
            Container(container["image"], index, "containers")
            for index, container in enumerate(spec["containers"])
        ]
        init_container_list = [
            Container(container["image"], index, "initContainers")
            for index, container in enumerate(spec.get("initContainers", []))
        ]

        return container_list + init_container_list

    def get_json_patch(self, container: Container):
        return {
            "op": "replace",
            "path": self.container_path.format(
                container_type=container.container_type, index=container.index
            ),
            "value": str(container.image),
        }


class Pod(WorkloadObject):
    container_path = "/spec/{container_type}/{index}/image"

    @property
    def containers(self):
        container_list = [
            Container(container["image"], index, "containers")
            for index, container in enumerate(self._spec["containers"])
        ]
        init_container_list = [
            Container(container["image"], index, "initContainers")
            for index, container in enumerate(self._spec.get("initContainers", []))
        ]

        return container_list + init_container_list


class CronJob(WorkloadObject):
    container_path = (
        "/spec/jobTemplate/spec/template/spec/{container_type}/{index}/image"
    )

    @property
    def containers(self):
        spec = self._spec["jobTemplate"]["spec"]["template"]["spec"]
        container_list = [
            Container(container["image"], index, "containers")
            for index, container in enumerate(spec["containers"])
        ]
        init_container_list = [
            Container(container["image"], index, "initContainers")
            for index, container in enumerate(spec.get("initContainers", []))
        ]

        return container_list + init_container_list
