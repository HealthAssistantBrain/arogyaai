from pipelines.feature_pipeline.service import FeaturePipelineService, FeatureSnapshot, _clamp


class FeatureService:
    @staticmethod
    def build_feature_snapshot(db, user, overrides: dict | None = None):
        return FeaturePipelineService.build_feature_snapshot(db, user, overrides=overrides, persist=True)
