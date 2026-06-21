FROM python:3.11-slim

# Install Node.js 20 LTS + curl
RUN apt-get update \
  && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
  && mkdir -p /etc/apt/keyrings \
  && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
     | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
  && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" \
     > /etc/apt/sources.list.d/nodesource.list \
  && apt-get update \
  && apt-get install -y --no-install-recommends nodejs \
  && rm -rf /var/lib/apt/lists/*

# Install uv via official install script (avoids COPY --from ghcr.io issues)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy dependency files first (better layer caching)
COPY package.json ./
COPY frontend/package.json ./frontend/
COPY backend/pyproject.toml backend/uv.lock ./backend/

# Install all dependencies
RUN npm install --legacy-peer-deps \
  && npm install --prefix frontend --legacy-peer-deps \
  && cd backend && uv sync --frozen

# Copy full source
COPY . .

EXPOSE 3000 5001

CMD ["npm", "run", "dev"]
