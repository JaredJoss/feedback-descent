from __future__ import annotations

from feedback_descent.domains.base import DomainPlugin

_registry: dict[str, DomainPlugin] = {}


def register_domain(plugin: DomainPlugin) -> None:
    _registry[plugin.name] = plugin


def get_domain(name: str) -> DomainPlugin:
    if name not in _registry:
        available = list(_registry.keys())
        raise ValueError(f"Unknown domain {name!r}. Available: {available}")
    return _registry[name]


def list_domains() -> list[str]:
    return sorted(_registry.keys())


def _register_builtins() -> None:
    from feedback_descent.domains.svg import SVGDomain

    register_domain(SVGDomain())


_register_builtins()
