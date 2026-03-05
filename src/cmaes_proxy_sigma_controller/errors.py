from __future__ import annotations


class ControllerError(Exception):
    """Base class for controller errors."""


class ConfigValidationError(ControllerError, ValueError):
    """Raised when controller configuration is invalid."""


class InputValidationError(ControllerError, ValueError):
    """Raised when controller input is invalid."""


class StateValidationError(ControllerError, ValueError):
    """Raised when controller state is invalid or inconsistent."""


class StepExecutionError(ControllerError, RuntimeError):
    """Raised when step execution fails under fail-fast mode."""


class SigmaDriftError(ControllerError, RuntimeError):
    """Raised when host sigma mutation violates adapter contract."""
