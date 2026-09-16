"""AWS Lambda entry point: the same FastAPI app, wrapped with Mangum behind
a function URL. The only difference from local is the store, selected by
BELLWETHER_TABLE in main.py. Deployed by the CDK stack in infra/."""

from mangum import Mangum

from .main import app

handler = Mangum(app, lifespan="off")
