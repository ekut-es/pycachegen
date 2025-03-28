# base image
FROM python:3.10.15-slim-bullseye

# install apt packages
RUN apt -y update
RUN apt -y upgrade
