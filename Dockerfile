# Alpine pyhon image with uv installed
FROM ghcr.io/astral-sh/uv:0.8-python3.13-alpine

# Install psycopg2-binary
RUN apk add build-base libpq libpq-dev && apk add libffi-dev

# Install the project into `/app`
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

## Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
COPY . /app
RUN uv sync --frozen --no-goup production

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT ["sh", "/app/docker/entrypoint.sh"]
