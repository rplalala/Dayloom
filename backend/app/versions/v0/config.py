"""Environment-backed configuration for the V0 runtime."""

from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import SettingsConfigDict

from backend.app.runtime.deployment import DEPLOYMENT_FILE, DeploymentYamlSettingsSource
from backend.app.runtime.settings import RuntimeSettings


class V0Settings(RuntimeSettings):
    """Configuration required to run V0 through Microsoft Foundry."""

    model_config = SettingsConfigDict(yaml_file=DEPLOYMENT_FILE, hide_input_in_errors=True)

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings
    ):
        return (
            init_settings, env_settings, dotenv_settings, file_secret_settings,
            DeploymentYamlSettingsSource(settings_cls, section="foundry", aliases={
                "endpoint": "AZURE_OPENAI_ENDPOINT", "deployment": "AZURE_OPENAI_DEPLOYMENT",
            }),
        )

    azure_openai_endpoint: AnyHttpUrl = Field(
        validation_alias="AZURE_OPENAI_ENDPOINT",
    )
    azure_openai_deployment: str = Field(
        min_length=1,
        validation_alias="AZURE_OPENAI_DEPLOYMENT",
    )
    azure_openai_api_key: SecretStr = Field(
        min_length=1,
        validation_alias="AZURE_OPENAI_API_KEY",
    )
