from fastapi import Depends
from ..models import Tenant
from .auth import get_current_tenant

def current_tenant(tenant: Tenant = Depends(get_current_tenant)) -> Tenant:
    """Compatibilidade com os routers existentes da V4.

    Na V5 o tenant vem do usuário autenticado pelo JWT, e não de cabeçalho enviado
    pelo navegador.
    """
    return tenant
