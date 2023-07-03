#!/usr/bin/env bash


# kill running containers
docker kill $(docker ps -q)

# delete all stopped containers
docker rm $(docker ps -a -q)

# delete all images
docker rmi $(docker images -a -q)

# delete all volumes
docker volume rm $(docker volume ls -q)
