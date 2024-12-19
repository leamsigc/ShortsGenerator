# Dockerfile
FROM python:3.10

# Install system dependencies
RUN apt-get -y update && \
    apt-get -y install --no-install-recommends \
    ffmpeg \
    imagemagick \
    procps \
    fonts-liberation && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set up locale
RUN apt-get update && apt-get install -y locales && \
    locale-gen C.UTF-8 && \
    /usr/sbin/update-locale LANG=C.UTF-8 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV LC_ALL C.UTF-8

# Modify ImageMagick policy to allow text operations
RUN sed -i 's/none/read,write/g' /etc/ImageMagick-6/policy.xml 

# Set environment variables
# ENV IMAGEMAGICK_BINARY=/usr/bin/convert
ENV PYTHONUNBUFFERED=1

WORKDIR /home/app

# Copy only necessary files
COPY requirements.txt .
COPY Backend/ Backend/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


WORKDIR /home/app/Backend
# copy the .env file
COPY .env .

# Default command
CMD ["python", "main.py"]
