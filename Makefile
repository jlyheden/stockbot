.PHONY: setup
setup: ; docker-compose rm -f && docker-compose down --rmi local -v && docker-compose up --build -d

.PHONY: rebuild
rebuild: ; docker-compose stop ircbot && docker-compose rm -f ircbot && docker-compose build ircbot && docker-compose up -d ircbot
