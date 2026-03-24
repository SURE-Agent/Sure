"""Helpers de credenciales de Azure."""

from azure.identity import (
    ChainedTokenCredential,
    DeviceCodeCredential,
    ManagedIdentityCredential,
)

from src.config import TENANT_ID


def get_credential() -> ChainedTokenCredential:
    """Retorna una cadena de credenciales que funciona en Docker local y App Service.

    Orden de prioridad:
        1. ManagedIdentityCredential  – App Service / producción en Azure
        2. DeviceCodeCredential       – Docker local (muestra código en terminal)
    """
    return ChainedTokenCredential(
        ManagedIdentityCredential(),
        DeviceCodeCredential(tenant_id=TENANT_ID),
    )
