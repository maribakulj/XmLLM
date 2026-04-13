"""Provider resolver — resolves a ProviderProfile into runtime + adapter."""

from __future__ import annotations

from src.app.providers.adapters.base import BaseAdapter
from src.app.providers.profiles import ProviderProfile
from src.app.providers.registry import get_adapter, get_runtime
from src.app.providers.runtimes.base import BaseRuntime


class ResolvedProvider:
    """A fully resolved provider: runtime + adapter, ready to execute."""

    def __init__(self, profile: ProviderProfile, runtime: BaseRuntime, adapter: BaseAdapter) -> None:
        self.profile = profile
        self.runtime = runtime
        self.adapter = adapter

    @property
    def provider_id(self) -> str:
        return self.profile.provider_id

    @property
    def family(self) -> str:
        return self.profile.family.value


def resolve_provider(profile: ProviderProfile) -> ResolvedProvider:
    """Resolve a provider profile into a runtime + adapter pair.

    No magic: the profile explicitly declares its runtime_type and family.
    We look them up in the registries.

    Raises KeyError if the runtime or family is not registered.
    """
    runtime = get_runtime(profile.runtime_type.value)
    adapter = get_adapter(profile.family.value)
    return ResolvedProvider(profile=profile, runtime=runtime, adapter=adapter)
