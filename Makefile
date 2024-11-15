#Makefile

clean:
	@echo "Cleaning Dangle Image" 
	docker system prune -a

build: clean
	@echo "building docker image" 
	docker build -t generate_primary_key .

run: build
	@echo "running docker image" 
	docker run generate_primary_key

push:
	@echo "pushing docker image"
	docker tag generate_primary_key shoaibswe/generate_primary_key:latest
	docker push shoaibswe/generate_primary_key:latest

compose-up:
	@echo "starting services with docker-compose"
	docker-compose up --build

compose-down:
	@echo "stopping services with docker-compose"
	docker-compose down
