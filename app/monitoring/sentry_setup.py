import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration


def setup_sentry() -> None:
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return
    sentry_sdk.init(
        dsn=dsn,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.05,
        environment=os.getenv("ENVIRONMENT", "development"),
        release=os.getenv("VERSION", "unknown"),
    )
