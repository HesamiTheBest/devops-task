.PHONY: up down logs ps clean

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
	docker compose down -v
