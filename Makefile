IMAGE=hesammardani/devops-task
VERSION=1.0.0

.PHONY: up down logs ps clean dev

up:
	cp -n .env.example .env
	docker compose up -d --build
	docker compose restart nginx
down: 
	docker compose down

logs: 
	docker compose logs -f api

ps:
	docker compose ps

clean:
	docker compose down -v
	
dev:
	cp -n .env.example .env
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build 

push:
	docker build -t $(IMAGE):$(VERSION) .
	docker tag $(IMAGE):$(VERSION) $(IMAGE):latest
	docker tag $(IMAGE):$(VERSION) $(IMAGE):$(shell git rev-parse --short HEAD)
	docker push $(IMAGE) --all-tags