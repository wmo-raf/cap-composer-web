# syntax = docker/dockerfile:1.5

# use osgeo gdal ubuntu small 3.7 image as base
# pre-installed with GDAL 3.7.0 and Python 3.10.6
FROM ghcr.io/osgeo/gdal:ubuntu-small-3.7.0

# Add user that will be used in the container.
RUN useradd cap

# install dependencies
RUN apt-get update && apt-get install -y \
    lsb-release \
    python3-pip --fix-missing \
    libgeos-dev \
    imagemagick \
    libmagic1 \
    libcairo2-dev

# for pg_dump
RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list \
    && cat /etc/apt/sources.list.d/pgdg.list \
    && curl --silent https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add - \
    && apt-get update \
    && apt-get install -y postgresql-client-15

# set python env
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install docker-compose wait utility to wait for other docker images to be started while using docker-compose
# https://github.com/ufoscout/docker-compose-wait
ADD https://github.com/ufoscout/docker-compose-wait/releases/download/2.12.1/wait /wait
RUN chmod +x /wait

# Install the project requirements.
COPY requirements.txt /
RUN --mount=type=cache,target=/root/.cache pip install --upgrade pip \
    && pip install "gunicorn==20.0.4" \
    && pip install -r requirements.txt

# Use /app folder as a directory where the source code is stored.
WORKDIR /app

COPY docker/capsite/entrypoint.sh ./
RUN chmod +x entrypoint.sh

# Set this directory to be owned by the "cap" user
RUN chown cap:cap /app

# Copy the source code of the project into the container.
COPY --chown=cap:cap . .

# Use user "cap" to run the container
USER cap

CMD /wait && ./entrypoint.sh