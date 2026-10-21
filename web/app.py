import os
import time

import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, g, Response, abort, jsonify
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

DB = dict(
    host=os.getenv("DB_HOST", "db"),
    dbname=os.getenv("DB_NAME", "recipes"),
    user=os.getenv("DB_USER", "recipe"),
    password=os.getenv("DB_PASSWORD", "recipe"),
    connect_timeout=3,
)

# --- Prometheus metrics ---
REQS = Counter("http_requests_total", "HTTP requests", ["method", "endpoint", "status"])
LAT = Histogram("http_request_duration_seconds", "Total request time (Flask)", ["endpoint"])
DBLAT = Histogram("db_query_duration_seconds", "Time spent in PostgreSQL", ["query"])


def query(name, sql, params=()):
    start = time.perf_counter()
    conn = psycopg2.connect(**DB)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        conn.close()
        DBLAT.labels(name).observe(time.perf_counter() - start)


@app.before_request
def start_timer():
    g.t0 = time.perf_counter()


@app.after_request
def record(resp):
    if request.path != "/metrics":
        ep = request.endpoint or "not_found"
        REQS.labels(request.method, ep, str(resp.status_code)).inc()
        LAT.labels(ep).observe(time.perf_counter() - g.t0)
    return resp


@app.errorhandler(psycopg2.Error)
def db_down(e):
    app.logger.error("Database error: %s", e)
    return render_template("error.html"), 503


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", not_found=True), 404


@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    if q:
        like = f"%{q}%"
        recipes = query(
            "search",
            "SELECT id, title, category, emoji, description, cook_time FROM recipes "
            "WHERE title ILIKE %s OR category ILIKE %s OR ingredients ILIKE %s ORDER BY title",
            (like, like, like),
        )
    else:
        recipes = query(
            "list",
            "SELECT id, title, category, emoji, description, cook_time FROM recipes ORDER BY title",
        )
    return render_template("index.html", recipes=recipes, q=q)


@app.route("/recipe/<int:recipe_id>")
def recipe(recipe_id):
    rows = query("detail", "SELECT * FROM recipes WHERE id = %s", (recipe_id,))
    if not rows:
        abort(404)
    r = rows[0]
    return render_template(
        "recipe.html",
        r=r,
        ingredients=r["ingredients"].split("\n"),
        steps=r["steps"].split("\n"),
    )


@app.route("/health")
def health():
    query("health", "SELECT 1")
    return jsonify(status="ok")


@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


# --- Demo endpoints: show in Grafana WHERE slowness comes from ---
@app.route("/demo/slow-app")
def slow_app():
    time.sleep(1.0)  # slowness inside Flask: request latency up, DB latency flat
    return "slow app done"


@app.route("/demo/slow-db")
def slow_db():
    query("demo_slow", "SELECT pg_sleep(1)")  # slowness inside DB: both go up
    return "slow db done"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
