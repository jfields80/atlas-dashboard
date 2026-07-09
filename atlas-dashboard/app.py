from flask import Flask

from services.opportunity_v2.bootstrap import boot_atlas
from services.opportunity_v2.runtime_context import runtime

from routes.categories import categories_bp
from routes.dashboard import dashboard_bp
from routes.projects import projects_bp
from routes.businesses import businesses_bp
from routes.scout import scout_bp
from routes.employees import employees_bp
from routes.analytics import analytics_bp
from routes.settings import settings_bp
from routes.sources import sources_bp
from routes.opportunities import opportunities_bp
from routes.orchestrator_runs import orchestrator_runs_bp
from routes.operations import operations_bp


app = Flask(__name__)
app.secret_key = "atlas-dev-secret-key"


# ─────────────────────────────────────────────
# SAFE BOOT SEQUENCE (CRITICAL FIX)
# ─────────────────────────────────────────────

runtime.initialize()
boot_atlas()


# ─────────────────────────────────────────────
# BLUEPRINTS
# ─────────────────────────────────────────────

app.register_blueprint(categories_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(projects_bp)
app.register_blueprint(businesses_bp)
app.register_blueprint(scout_bp)
app.register_blueprint(employees_bp)
app.register_blueprint(analytics_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(sources_bp)
app.register_blueprint(opportunities_bp)
app.register_blueprint(orchestrator_runs_bp)
app.register_blueprint(operations_bp)


print("\n===================")
print(app.url_map)
print("===================\n")


if __name__ == "__main__":
    app.run(debug=True)