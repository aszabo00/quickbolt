# Stage 1: Build dependencies
FROM python:3.13

# Set the working directory
WORKDIR /quickbolt

# Copy only the dependency files to the container
COPY pyproject.toml poetry.lock ./

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry's install path
ENV PATH="${PATH}:/root/.local/bin"

# Install project dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-root

# Set the environment variables
ENV PYTHONPATH="/workspaces/quickbolt:/quickbolt"
ENV PYTHONUNBUFFERED 1

# Copy the application code
COPY . .
