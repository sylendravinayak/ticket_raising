from src.api.middleware.logging import setup_logging
from src.api.rest.app import create_app
setup_logging(debug=True)
app = create_app()