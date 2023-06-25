# Stage 1: Build dependencies
FROM python:3.11 AS builder
# FROM python:3.11-slim

# # Install system dependencies required for Poetry and other packages
# RUN apt-get update && \
#     apt-get install -y --no-install-recommends curl build-essential && \
#     rm -rf /var/lib/apt/lists/* && \
#     rm -rf ~/.cache/*

# Set the working directory
WORKDIR /quickbolt

# Copy only the dependency files to the container
COPY pyproject.toml ./
# COPY pyproject.toml poetry.lock ./

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry's install path
ENV PATH="${PATH}:/root/.local/bin"

# Install project dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-root

# # Stage 2: Build application image
# FROM python:3.11-slim

# # Install curl
# RUN apt-get update && apt-get install -y curl

# # Install Poetry
# RUN curl -sSL https://install.python-poetry.org | python3 -

# # Add Poetry's install path
# ENV PATH="${PATH}:/root/.local/bin"

# # Set the working directory
# WORKDIR /quickbolt

# # Copy only the necessary files from the builder stage
# COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
# COPY --from=builder /quickbolt .

# Set the environment variables
ENV PYTHONPATH="/quickbolt"
ENV PYTHONUNBUFFERED 1
# ENV PYTHONDONTWRITEBYTECODE 1

# Copy the application code
COPY . .
