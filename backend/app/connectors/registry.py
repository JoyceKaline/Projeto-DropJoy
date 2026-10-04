from .demo import DemoConnector
from .dropify import DropifyConnector

CONNECTORS = {
    "demo": DemoConnector,
    "dropify": DropifyConnector,
}

def connector_for(slug: str):
    klass = CONNECTORS.get(slug)
    return klass() if klass else None
