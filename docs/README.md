# Welcome to Connaisseur

A Kubernetes admission controller to integrate container image signature verification and trust pinning into a cluster.

## What is Connaisseur?

Connaisseur ensures integrity and provenance of container images in a Kubernetes cluster. To do so, it intercepts resource creation or update requests sent to the Kubernetes cluster, identifies all container images and verifies their signatures against pre-configured public keys. Based on the result, it either accepts or denies those requests.

Connaisseur is developed under three core values: *Security*, *Usability*, *Compatibility*. It is built to be extendable and currently aims to support the following signing solutions:

- [Notary V1](https://github.com/theupdateframework/notary) / [Docker Content Trust](https://docs.docker.com/engine/security/trust/)
- [Sigstore](https://sigstore.dev/) / [Cosign](https://github.com/sigstore/cosign) (EXPERIMENTAL)
- [Notary V2](https://github.com/notaryproject/nv2) (PLANNED)

It provides several additional features:

- [Detection Mode](features/detection_mode.md): *warn but do not block invalid images*
- [Namespaced Validation](features/namespaced_validation.md): *restrict validation to dedicated namespaces*
- [Alerting](features/alerting.md): *send alerts based on verification result*

Feel free to reach out to us via [GitHub Discussions](https://github.com/sse-secure-systems/connaisseur/discussions)!

## Quick Start

Getting started to verify image signatures is only a matter of minutes: 

![](assets/connaisseur_demo.gif)

> :warning: Only try this out on a test cluster as deployments with unsigned images will be blocked. :warning:

Connaisseur comes pre-configured with public keys for its own repository and [Docker's official images](https://docs.docker.com/docker-hub/official_images/) (for a list of official images check [here](https://hub.docker.com/search?q=&type=image&image_filter=official)).
It can be fully configured via `helm/values.yaml`.
For a quick start, clone the Connaisseur repository:

```bash
git clone https://github.com/sse-secure-systems/connaisseur.git
```

Next, install Connaisseur via [Helm](https://helm.sh):

```bash
helm install connaisseur helm --atomic --create-namespace --namespace connaisseur
```

Once installation has finished, you are good to go. Successful verification can be tested via official Docker images like `hello-world`:

```bash
kubectl run hello-world --image=docker.io/hello-world
```

Or our signed `testimage`:

```bash
kubectl run demo --image=docker.io/securesystemsengineering/testimage:signed
```

Both will return `pod/<name> created`. However, when trying to deploy an unsigned image:

```bash
kubectl run demo --image=docker.io/securesystemsengineering/testimage:unsigned
```

Connaisseur returns an error `(...) Unable to find signed digest (...)`. Since the images above are signed using Docker Content Trust, you can inspect the trust data using `docker trust inspect --pretty <image-name>`.

To uninstall Connaisseur use:

```bash
helm uninstall connaisseur --namespace connaisseur
```

To uninstall all components add the `--purge` flag.

Congrats :tada: you just validated the first images in your cluster! To get started configuring and verifying your own images and signatures, please follow our full [setup guide](getting_started.md).


## How does it work?

Digital signatures can be used to ensure integrity and provenance of container images deployed to a Kubernetes cluster. On a very basic level, this requires two steps:

1. Signing container images *after building*
2. Verifying the image signatures *before deployment*

Connaisseur dedicatedly solves the second step. It implements signature verification via several available signing schemes that we refer to as *validators*.
While the specific security primitives mainly depend on the applied signing scheme, Connaisseur in general verifies the signature over the container image content against a trust anchor (e.g. public key) and thus let's you ensure that images have not been tampered with (integrity) and come from a valid source (provenance). 

![](./assets/sign-verify.png)

### Trusted digests

Container images can be referenced in two different ways based on their registry, repository, image name (`<registry>/<repository>/<image name>`) followed by tag or digest:

- tag: *docker.io/library/nginx:****1.20.1***
- digest: *docker.io/library/nginx@****sha256:af9c...69ce***

While the tag is a mutable, human readable description, the digest is an immutable, inherent property of the image, namely the SHA256 hash of its content.
As a result a tag can have multiple digests whereas digests are unique for each image.
In fact, the container runtime (e.g. containerd) compares the image content against the digest before spinning up the container (CHECK!!).
As a consequence, the image digest can be signed and Connaisseur just needs to either translate an image referenced by tag to a trusted (signed by a trusted entity) digest or, in case of an image referenced by digest, validate whether the digest is trusted.

### Admission control

### Workflow

## Compatibility

Supported signature solutions and configuration options are documented under [Validators](./validators/README.md).

Connaisseur is expected to be compatible with most Kubernetes services. It has been successfully tested with:

- [K3s](https://github.com/rancher/k3s) ✅
- [kind](https://kind.sigs.k8s.io/) ✅
- [MicroK8s](https://github.com/ubuntu/microk8s) ✅
- [minikube](https://github.com/kubernetes/minikube) ✅
- [Amazon Elastic Kubernetes Service (EKS)](https://docs.aws.amazon.com/eks/) ✅
- [Azure Kubernetes Service (AKS)](https://docs.microsoft.com/en-us/azure/aks/) ✅
- [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine/docs/) ✅
- [SysEleven MetaKube](https://docs.syseleven.de/metakube) ✅

All registry interactions use the [OCI Distribution Specification](https://github.com/opencontainers/distribution-spec/blob/main/spec.md) that is based on the [Docker Registry HTTP API V2](https://docs.docker.com/registry/spec/api/) which is the standard for all common image registries.
For using Notary V1 as a signature solution, some registries provide the required Notary server attached to the registry with e.g. shared authentication. Connaisseur has been tested with the following Notary V1 supporting image registries:

- [Docker Hub](https://hub.docker.com/) ✅
- [Harbor](https://goharbor.io/) ✅ (check our [configuration notes](./validators/notaryv1.md#using-harbor-container-registry))
- [Azure Container Registry (ACR)](https://docs.microsoft.com/en-us/azure/container-registry/) ✅ (check our [configuration notes](./validators/notaryv1.md#using-azure-container-registry))

In case you identify any incompatibilities, please [create an issue](https://github.com/sse-secure-systems/connaisseur/issues/new/choose) :hearts:

## Development

Connaisseur is open source and open development. We try to make major changes transparent via [*Architecture Decision Records* (ADRs)](./adr/README.md) and announce developments via [GitHub Discussions](https://github.com/sse-secure-systems/connaisseur/discussions/categories/announcements).

We hope to get as many direct contributions and insights from the community as possible to steer further development. Please refer to our [contributing guide](CONTRIBUTING.md), [create an issue](https://github.com/sse-secure-systems/connaisseur/issues/new/choose) or [reach out to us via GitHub Discussions](https://github.com/sse-secure-systems/connaisseur/discussions) :pray:

## Resources

Several resources are available to learn more about connaisseur and related topics:

- "[*Container Image Signatures in Kubernetes*](https://medium.com/sse-blog/container-image-signatures-in-kubernetes-19264ac5d8ce)" - blog post (full introduction)
- "[*Integrity of Docker images*](https://berlin-crypto.github.io/event/dockerimagesignatures.html)" - talk at Berlin Crypto Meetup (*The Update Framework*, *Notary*, *Docker Content Trust* & Connaisseur [live demo])
- "[*Verifying Container Image Signatures from an OCI Registry in Kubernetes*](https://blog.sigstore.dev/verify-oci-container-image-signatures-in-kubernetes-33663a9ec7d8)" - blog post (experimental support of SigStore/Cosign)

