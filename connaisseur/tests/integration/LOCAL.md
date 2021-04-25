# Local integration test setup

## Minikube

Assuming you have a running minikube cluster set as current kubernetes context you just need to have the alerting interface running.

Run the docker container that serves as alerting endpoint and retrieve the IP address that it has on the `bridge` network:

```shell
docker run -d --name alerting-endpoint -p 56243:56243 docker.io/securesystemsengineering/alerting-endpoint:latest
export ALERTING_ENDPOINT_IP=$(docker container inspect alerting-endpoint | jq -r .[].NetworkSettings.Networks.bridge.IPAddress)
```

From the git repository folder run the `connaisseur/tests/integration/integration-test.sh` script.

To cleanup the mocked alerting interface container don't forget running 

```shell
docker stop alerting-endpoint
docker rm alerting-endpoint
```

## Kind

For kind we assume you have a running kind cluster set as current kubernetes context and that you have loaded the docker images from the latest connaisseur image version as well as the hook image onto the `kind` nodes.
You need to have the alerting interface running and attach it to the docker network that is used by the kind container. By default, it's name is `kind`, so if you renamed the docker network of the kind container provide your custom name as `KIND_NETWORK`: 

```shell
KIND_NETWORK=kind
docker run -d --name alerting-endpoint -p 56243:56243 docker.io/securesystemsengineering/alerting-endpoint:latest
docker network connect ${KIND_NETWORK} alerting-endpoint
export ALERTING_ENDPOINT_IP=$(docker container inspect alerting-endpoint | jq -r --arg kind_network ${KIND_NETWORK} '.[].NetworkSettings.Networks[$kind_network].IPAddress')
```

From the git repository run the `connaisseur/tests/integration/integration-test.sh` script.

Obviously, we don't want to leave unused resources running, so stop and remove the alerting interface docker container  as in the minikube case :-)
