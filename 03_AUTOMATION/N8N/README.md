# n8n Local Evaluation

- Container name: `n8n-local-automation`
- Image: `docker.n8n.io/n8nio/n8n:latest`
- Host binding: `127.0.0.1:5678 -> 5678`
- Data path: `C:\AI_WORKFLOW\03_AUTOMATION\N8N\data`
- Purpose in Fase 5: local evaluation only, no workflows active by default, no production exposure

Useful commands:

- `docker ps --filter "name=n8n-local-automation"`
- `docker stop n8n-local-automation`
- `docker start n8n-local-automation`
- `docker logs --tail 80 n8n-local-automation`
