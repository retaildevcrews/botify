# Run Application Locally

**NOTE: In order to do this, you must have cloned the repository or opened up the repository in a code space.  If attempting to run locally, docker daemon must be runnning on your system.**

Running the following Docker Compose command will build the latest images and then run them with the required networking, secrets, services, and port forwarding. Open [docker-compose.yaml](../../apps/docker-compose.yaml) for more info.

```bash
cd apps
docker compose up -w
```

You can access the StreamLit test bot here: <http://localhost:8000>
