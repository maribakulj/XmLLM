"""Provider registry — central index of available adapters and runtimes."""

from __future__ import annotations

from src.app.providers.adapters.base import BaseAdapter
from src.app.providers.adapters.line_box_json import LineBoxJsonAdapter
from src.app.providers.adapters.text_only import TextOnlyAdapter
from src.app.providers.adapters.word_box_json import WordBoxJsonAdapter
from src.app.providers.profiles import ProviderFamily, RuntimeType
from src.app.providers.runtimes.api_runtime import ApiRuntime
from src.app.providers.runtimes.base import BaseRuntime
from src.app.providers.runtimes.hub_runtime import HubRuntime
from src.app.providers.runtimes.local_runtime import LocalRuntime

# -- Adapter registry ---------------------------------------------------------

_ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {
    ProviderFamily.WORD_BOX_JSON.value: WordBoxJsonAdapter,
    ProviderFamily.LINE_BOX_JSON.value: LineBoxJsonAdapter,
    ProviderFamily.TEXT_ONLY.value: TextOnlyAdapter,
}


def get_adapter(family: str) -> BaseAdapter:
    """Instantiate an adapter for the given provider family."""
    cls = _ADAPTER_REGISTRY.get(family)
    if cls is None:
        raise KeyError(
            f"No adapter for family '{family}'. "
            f"Available: {list(_ADAPTER_REGISTRY.keys())}"
        )
    return cls()


def list_adapter_families() -> list[str]:
    return list(_ADAPTER_REGISTRY.keys())


# -- Runtime registry ---------------------------------------------------------

_RUNTIME_REGISTRY: dict[str, type[BaseRuntime]] = {
    RuntimeType.LOCAL.value: LocalRuntime,
    RuntimeType.HUB.value: HubRuntime,
    RuntimeType.API.value: ApiRuntime,
}


def get_runtime(runtime_type: str, **kwargs: object) -> BaseRuntime:
    """Instantiate a runtime for the given type."""
    cls = _RUNTIME_REGISTRY.get(runtime_type)
    if cls is None:
        raise KeyError(
            f"No runtime for type '{runtime_type}'. "
            f"Available: {list(_RUNTIME_REGISTRY.keys())}"
        )
    return cls(**kwargs)  # type: ignore[arg-type]


def list_runtime_types() -> list[str]:
    return list(_RUNTIME_REGISTRY.keys())
