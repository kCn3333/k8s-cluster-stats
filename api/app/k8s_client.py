from kubernetes import client, config

_clients: tuple | None = None


def get_clients() -> tuple[client.CoreV1Api, client.CustomObjectsApi]:
    global _clients
    if _clients is not None:
        return _clients
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    _clients = (client.CoreV1Api(), client.CustomObjectsApi())
    return _clients
