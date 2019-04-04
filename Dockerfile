FROM ubuntu
#
# FogLAMP 1.5.0 on IOx
# 

# Set Timezone information or install will ask and hang up docker build
ENV TZ=America/New_York
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install packages required for FogLAMP
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
    apt-utils \
    autoconf \ 
    automake \
    avahi-daemon \
    build-essential \
    cmake \
    curl \
    g++ \
    git \
    libboost-dev \
    libboost-system-dev \
    libboost-thread-dev \
    libpq-dev \
    libsqlite3-dev \
    libssl-dev \
    libtool \
    libz-dev \
    make \
    postgresql \
    python3-dev \
    python3-pip \
    python3-dbus \
    python3-setuptools \
    rsyslog \
    sqlite3 \
    uuid-dev \
&& apt-get clean \
&& rm -rf /var/lib/apt/lists/*

WORKDIR /foglamp
RUN mkdir -p /foglamp \
&& git clone https://github.com/foglamp/FogLAMP.git /foglamp \
&& git checkout v1.5.1 \
&& make \
&& make install

RUN pip3 install pymodbus

ENV FOGLAMP_ROOT=/usr/local/foglamp

RUN mkdir -p /usr/local/foglamp/python/foglamp/plugins/north/http_north
COPY plugins/north/http_north /usr/local/foglamp/python/foglamp/plugins/north/http_north

RUN mkdir -p /usr/local/foglamp/python/foglamp/plugins/south/b100
COPY plugins/south/b100 /usr/local/foglamp/python/foglamp/plugins/south/b100

RUN mkdir -p /usr/local/foglamp/plugins/south/random
COPY plugins/south/random /usr/local/foglamp/plugins/south/random

RUN mkdir -p /usr/local/foglamp/python/foglamp/plugins/south/systeminfo
COPY plugins/south/systeminfo /usr/local/foglamp/python/foglamp/plugins/south/systeminfo

WORKDIR /usr/local/foglamp
COPY foglamp.sh .

VOLUME /usr/local/foglamp/data

# FogLAMP API port
EXPOSE 8081 1995

# start rsyslog, FogLAMP, and tail syslog
CMD ["bash","/usr/local/foglamp/foglamp.sh"]

LABEL maintainer="rob@raesemann.com" \
      author="Raesemann" \
      target="IOx" \
      version="1.5.1" \