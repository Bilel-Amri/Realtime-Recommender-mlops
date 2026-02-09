# Real-Time Recommender System - Model Registration Module
"""
Model registration and promotion pipeline.

This module provides:
- Model registration to MLflow Model Registry
- Stage promotion (None -> Staging -> Production)
- Model versioning
- Rollback capabilities
- Model archival
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import mlflow
from mlflow import MlflowClient
try:
    from mlflow.entities.model_registry import ModelVersion
except ImportError:
    # Fallback for older MLflow versions
    ModelVersion = Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    MLflow Model Registry wrapper.

    Provides high-level operations for:
    - Registering new model versions
    - Promoting models through stages
    - Managing model transitions
    - Rolling back to previous versions
    """

    def __init__(
        self,
        registry_uri: Optional[str] = None,
        model_name: str = "recommender-model",
    ):
        """
        Initialize model registry.

        Args:
            registry_uri: MLflow registry URI
            model_name: Name of the model to manage
        """
        self.model_name = model_name
        self.client = MlflowClient(registry_uri or mlflow.get_registry_uri())

    def register_version(
        self,
        model_uri: str,
        version: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
    ) -> Any:
        """
        Register a new model version.

        Args:
            model_uri: URI of the model to register
            version: Version string (defaults to timestamp)
            description: Model description
            tags: Model tags

        Returns:
            Registered model version
        """
        # Create version string if not provided
        if version is None:
            version = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # Register model
        model_version = self.client.create_model_version(
            name=self.model_name,
            source=model_uri,
            run_id=mlflow.active_run().info.run_id if mlflow.active_run() else None,
            description=description,
            tags=tags,
        )

        logger.info(
            f"Registered model version: {self.model_name}/{model_version.version}"
        )

        return model_version

    def promote_to_staging(
        self,
        version: str,
        message: Optional[str] = None,
    ) -> Any:
        """
        Promote model version to Staging stage.

        Args:
            version: Model version to promote
            message: Transition message

        Returns:
            Transition request
        """
        request = self.client.transition_model_version_stage(
            name=self.model_name,
            version=version,
            stage="Staging",
            archive_existing_versions=True,
            description=message or "Promoted to staging for testing",
        )

        logger.info(
            f"Promoted {self.model_name}/{version} to Staging"
        )

        return request

    def promote_to_production(
        self,
        version: str,
        message: Optional[str] = None,
    ) -> Any:
        """
        Promote model version to Production stage.

        Args:
            version: Model version to promote
            message: Transition message

        Returns:
            Transition request
        """
        # First, archive current production version
        current_production = self.get_production_version()
        if current_production:
            self._archive_version(current_production.version)
            logger.info(
                f"Archived previous production version: {current_production.version}"
            )

        # Transition new version to production
        request = self.client.transition_model_version_stage(
            name=self.model_name,
            version=version,
            stage="Production",
            archive_existing_versions=False,
            description=message or "Promoted to production",
        )

        logger.info(
            f"Promoted {self.model_name}/{version} to Production"
        )

        return request

    def _archive_version(self, version: str) -> None:
        """Archive a model version."""
        self.client.transition_model_version_stage(
            name=self.model_name,
            version=version,
            stage="Archived",
            description="Archived by new production model",
        )

    def rollback_to_version(
        self,
        version: str,
        target_stage: str = "Production",
    ) -> Any:
        """
        Rollback to a specific model version.

        Args:
            version: Version to rollback to
            target_stage: Stage to promote to

        Returns:
            Transition request
        """
        # Archive current production
        current_production = self.get_production_version()
        if current_production and current_production.version != version:
            self._archive_version(current_production.version)

        # Promote target version
        request = self.client.transition_model_version_stage(
            name=self.model_name,
            version=version,
            stage=target_stage,
            description=f"Rollback to version {version}",
        )

        logger.info(
            f"Rolled back {self.model_name} to version {version} in {target_stage}"
        )

        return request

    def get_latest_versions(self, stages: Optional[List[str]] = None) -> List[Any]:
        """Get latest versions for each stage."""
        return self.client.get_latest_versions(self.model_name, stages)

    def get_production_version(self) -> Optional[Any]:
        """Get the current production version."""
        versions = self.get_latest_versions(stages=["Production"])
        return versions[0] if versions else None

    def get_staging_version(self) -> Optional[Any]:
        """Get the current staging version."""
        versions = self.get_latest_versions(stages=["Staging"])
        return versions[0] if versions else None

    def get_version_info(self, version: str) -> Dict[str, Any]:
        """Get detailed information about a model version."""
        mv = self.client.get_model_version(
            name=self.model_name,
            version=version,
        )

        return {
            "name": mv.name,
            "version": mv.version,
            "stage": mv.current_stage,
            "created_at": mv.creation_timestamp,
            "last_updated": mv.last_updated_timestamp,
            "description": mv.description,
            "tags": mv.tags,
            "run_id": mv.run_id,
            "source": mv.source,
        }

    def list_all_versions(self) -> List[Dict[str, Any]]:
        """List all versions of the model."""
        versions = []
        for mv in self.client.search_model_versions(f"name = '{self.model_name}'"):
            versions.append(self.get_version_info(mv.version))

        return sorted(versions, key=lambda x: x["created_at"], reverse=True)


def register_model(
    model_uri: str,
    model_name: str = "recommender-model",
    promote: bool = False,
    target_stage: str = "Staging",
) -> Dict[str, Any]:
    """
    Complete model registration and promotion pipeline.

    Args:
        model_uri: URI of the trained model
        model_name: Name for the model
        promote: Whether to promote after registration
        target_stage: Stage to promote to

    Returns:
        Dictionary with registration and promotion details
    """
    registry = ModelRegistry(model_name=model_name)

    # Register model
    model_version = registry.register_version(
        model_uri=model_uri,
        description=f"Recommendation model trained at {datetime.utcnow().isoformat()}",
        tags={"trained_at": datetime.utcnow().isoformat()},
    )

    result = {
        "model_name": model_name,
        "version": model_version.version,
        "stage": model_version.current_stage,
    }

    # Optionally promote
    if promote:
        if target_stage == "Production":
            registry.promote_to_production(model_version.version)
        else:
            registry.promote_to_staging(model_version.version)

        result["stage"] = target_stage

    return result


if __name__ == "__main__":
    # Example usage
    from train import train_model

    # Train model
    model, metrics = train_model()

    # Register model
    result = register_model(
        model_uri="runs:/<run_id>/model",
        promote=True,
        target_stage="Staging",
    )

    print(f"\nModel Registration Result:")
    print(f"  Name: {result['model_name']}")
    print(f"  Version: {result['version']}")
    print(f"  Stage: {result['stage']}")
