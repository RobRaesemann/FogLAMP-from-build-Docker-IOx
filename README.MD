
# FogLAMP Docker IOx Image

## Build and test for IOx

#### Reset the ioxclient profile
ioxclient profiles -reset

#### Build the Docker Image
docker build --rm -f "Dockerfile" -t jea-foglamp-iox:v1.5.0 .

#### Save the Docker image to rootfs.tar so that ioxclient can package
docker save -o IOx/rootfs.tar jea-foglamp-iox:v1.5.0

#### Build the package
ioxclient pkg IOx/.

#### Upload the package
ioxclient app install foglamp IOx/package.tar

## To test locally
#### Create the volume for FogLAMP data
docker create -v /usr/local/foglamp/data --name foglamp-data jea-foglamp-iox:v1.5.0 /bin/true

#### Run detached with autorestart
docker run --volumes-from foglamp-data -d -p 8081:8081 -p 80:80 -p 1995 jea-foglamp-iox:v1.5.0

#### Run interactively
docker run --volumes-from foglamp-data -it -p 8081:8081 -p 80:80 -p 1995 jea-foglamp-iox:v1.5.0 /bin/bash

#### Attach interactively to detached session
docker exec -it foglamp /bin/bash # get an interactive shell into running docker image

#### View logs
docker exec logs foglamp