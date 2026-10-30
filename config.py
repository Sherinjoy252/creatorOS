import os
from dotenv import load_dotenv

load_dotenv()

MESH_API_KEY = os.getenv("MESH_API_KEY", "")
MESH_BASE_URL = "https://api.meshapi.ai/v1"
MESH_MODEL = os.getenv("MESH_MODEL", "amazon/nova-micro-v1")
MESH_IMAGE_MODEL = os.getenv(
    "MESH_IMAGE_MODEL",
    "black-forest-labs/flux.1-schnell",
)


REQUEST_TIMEOUT_SECONDS = 120