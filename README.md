# IHK Recipe App

A containerized recipe web application developed as an IHK Cloud Engineer project.

## Architecture

- Flask — web application
- PostgreSQL — recipe database
- Docker Compose — runs the services
- Prometheus — collects application metrics
- Grafana — visualizes metrics in dashboards

## Features

- Browse and search recipes
- View recipe details
- Health endpoint: `/health`
- Metrics endpoint: `/metrics`

## Run the application

```bash
sudo docker compose up -d --build
```

## Services

- Recipe App: http://localhost:5000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

## Stop the application

```bash
sudo docker compose down
```

