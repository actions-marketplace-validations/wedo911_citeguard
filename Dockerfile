# Dockerfile for the citeguard MCP server.
#
# The MCP server lives in the mcp-server/ subdirectory of this monorepo and
# needs a TypeScript build step before it can run, so a plain "node
# index.js" won't work -- this image handles both. Used by MCP directory
# listings (e.g. Glama) that start the server and probe it with an
# introspection request, and usable directly by anyone who'd rather run
# the server in a container than install Node locally.
#
#   docker build -t citeguard-mcp .
#   docker run -i --rm citeguard-mcp

FROM node:22-alpine AS build

WORKDIR /app/mcp-server

# Install dependencies first so this layer is cached when only source changes.
COPY mcp-server/package.json mcp-server/package-lock.json ./
RUN npm ci

COPY mcp-server/tsconfig.json ./
COPY mcp-server/src ./src
RUN npm run build


FROM node:22-alpine AS runtime

WORKDIR /app/mcp-server
ENV NODE_ENV=production

COPY mcp-server/package.json mcp-server/package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

COPY --from=build /app/mcp-server/dist ./dist

# The server speaks MCP over stdio, so it must be run with an attached
# stdin (docker run -i). No network ports are exposed: the only outbound
# call it makes is to Crossref's public API.
CMD ["node", "dist/index.js"]
