# Deployment

For the complete local topology, copy `.env.example` to `.env` and run:

```bash
docker compose up -d --build
curl http://localhost:8000/health
```

The Compose file includes Redpanda, PostgreSQL, Redis, MinIO, MLflow, the recommendation API, a stream processor, Prometheus, and Grafana. Health checks gate the API and stream processor on Redpanda and Redis readiness.

The Kubernetes template can be applied after replacing the example image name and provisioning the referenced Redpanda and Redis services:

```bash
kubectl apply -f k8s/recommendation-api.yaml
kubectl rollout status deployment/recommendation-api
```

The Helm chart exposes the same controls through `values.yaml`:

```bash
helm lint helm/recommendation-platform
helm upgrade --install recommendations helm/recommendation-platform
```

These manifests are production-oriented templates with readiness probes, liveness probes, resource requests and limits, secrets, and horizontal scaling. They do not claim that a cluster has been deployed by this repository.
