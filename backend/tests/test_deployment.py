import pytest

from app.core.config import Settings


def test_demo_defaults_are_development_only():
    Settings(_env_file=None).validate_deployment()
    with pytest.raises(RuntimeError, match="Non-development startup refused"):
        Settings(_env_file=None, environment="production").validate_deployment()


def test_non_default_configuration_is_allowed():
    Settings(_env_file=None, environment="production", jwt_secret="x" * 40,
             demo_auditor_password="private-auditor-password",
             demo_manager_password="private-manager-password",
             database_url="sqlite:///local.db").validate_deployment()
