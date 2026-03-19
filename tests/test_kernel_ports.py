"""Tests for kernel port interfaces.

These tests verify that port interfaces follow the Protocol pattern
and have the required methods with correct signatures.
"""

import inspect
from typing import Any, get_type_hints

import pytest


def test_data_repository_is_protocol_with_add_method():
    """Test 1: DataRepository is a Protocol with async add() method."""
    from src.kernel.ports.repository import DataRepository

    # Verify it's a Protocol
    assert hasattr(DataRepository, "__protocol_attrs__")

    # Verify add() method exists with correct signature
    assert hasattr(DataRepository, "add")
    add_method = getattr(DataRepository, "add")
    sig = inspect.signature(add_method)

    # Check parameters
    assert "model" in sig.parameters
    assert "connection_id" in sig.parameters
    assert "data" in sig.parameters

    # Check return type annotation
    hints = get_type_hints(add_method)
    assert hints.get("return") == str


def test_data_repository_has_get_method():
    """Test 2: DataRepository has async get() method."""
    from src.kernel.ports.repository import DataRepository

    assert hasattr(DataRepository, "get")
    get_method = getattr(DataRepository, "get")
    sig = inspect.signature(get_method)

    # Check parameters
    assert "model" in sig.parameters
    assert "record_id" in sig.parameters

    # Check return type annotation
    hints = get_type_hints(get_method)
    return_type = hints.get("return")
    # Should be dict[str, Any] | None
    assert return_type is not None


def test_event_publisher_is_protocol_with_publish_method():
    """Test 3: EventPublisher is a Protocol with async publish() method."""
    from src.kernel.ports.event_publisher import EventPublisher

    # Verify it's a Protocol
    assert hasattr(EventPublisher, "__protocol_attrs__")

    # Verify publish() method exists
    assert hasattr(EventPublisher, "publish")
    publish_method = getattr(EventPublisher, "publish")
    sig = inspect.signature(publish_method)

    # Check parameters
    assert "event" in sig.parameters


def test_schema_registry_is_protocol_with_get_schema_method():
    """Test 4: SchemaRegistry is a Protocol with get_schema() method."""
    from src.kernel.ports.schema_registry import SchemaRegistry

    # Verify it's a Protocol
    assert hasattr(SchemaRegistry, "__protocol_attrs__")

    # Verify get_schema() method exists
    assert hasattr(SchemaRegistry, "get_schema")
    get_schema_method = getattr(SchemaRegistry, "get_schema")
    sig = inspect.signature(get_schema_method)

    # Check parameters
    assert "schema_name" in sig.parameters

    # Check return type annotation
    hints = get_type_hints(get_schema_method)
    return_type = hints.get("return")
    assert return_type is not None


def test_all_protocols_have_runtime_checkable_decorator():
    """Test 5: All protocols have runtime_checkable decorator."""
    from src.kernel.ports.repository import DataRepository
    from src.kernel.ports.event_publisher import EventPublisher
    from src.kernel.ports.schema_registry import SchemaRegistry

    # runtime_checkable adds _is_runtime_protocol attribute
    assert getattr(DataRepository, "_is_runtime_protocol", False)
    assert getattr(EventPublisher, "_is_runtime_protocol", False)
    assert getattr(SchemaRegistry, "_is_runtime_protocol", False)


def test_kernel_has_no_adapter_imports():
    """Kernel must not import from adapters (PERS-02).

    This enforces hexagonal architecture: adapters depend on kernel,
    never the reverse.
    """
    import ast
    from pathlib import Path

    kernel_dir = Path("src/kernel")
    violations = []

    for py_file in kernel_dir.rglob("*.py"):
        content = py_file.read_text()
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "adapters" in alias.name:
                        violations.append(f"{py_file}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and "adapters" in node.module:
                    violations.append(f"{py_file}: from {node.module} import ...")

    assert not violations, f"Kernel imports from adapters:\n" + "\n".join(violations)


def test_no_infrastructure_imports_in_port_files():
    """Test 6: No imports from sqlalchemy, fastapi, asyncpg in any port file."""
    import importlib.util
    import sys

    # Load the modules and check their source
    port_modules = [
        "src.kernel.ports.repository",
        "src.kernel.ports.event_publisher",
        "src.kernel.ports.schema_registry",
    ]

    forbidden_imports = ["sqlalchemy", "fastapi", "asyncpg"]

    for module_name in port_modules:
        # Get module file path
        spec = importlib.util.find_spec(module_name)
        if spec and spec.origin:
            with open(spec.origin, "r") as f:
                source = f.read()

            # Check for forbidden imports
            for forbidden in forbidden_imports:
                assert (
                    f"from {forbidden}" not in source
                    and f"import {forbidden}" not in source
                ), f"Found forbidden import '{forbidden}' in {module_name}"
