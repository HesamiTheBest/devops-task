.PHONY: up down logs ps clean dev

up:
	cp -n .env.example .env
	docker compose up -d --build

down: 
	docker compose down

logs: 
	docker compose logs -f api

ps:
	docker compose ps

clean:
	docker compose down -
	
dev:
	cp -n .env.example .env
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build 
