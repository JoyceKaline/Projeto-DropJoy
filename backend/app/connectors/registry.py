from .demo import DemoConnector
from .dropify import DropifyConnector
from .dslite import DSLiteConnector

CONNECTORS = {
    "demo": DemoConnector,
    "dropify": DropifyConnector,
    "dslite": DSLiteConnector,
}

def connector_for(slug: str):
    klass = CONNECTORS.get(slug)
    return klass() if klass else None
