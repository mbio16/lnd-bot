#!/bin/bash
#!/bin/bash
docker-compose -f docker-compose-mock.yaml --env-file .env_mock up  --build --force-recreate --no-deps -d 