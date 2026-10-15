# For MCP directories that introspect servers in a container (e.g. Glama).
# The Veilus desktop app is not in the image, so the launcher answers
# initialize and tools/list from the bundled catalog; tool calls return an
# error telling the user to install the app.
FROM node:22-slim
WORKDIR /app
COPY package.json tools.json ./
COPY bin ./bin
USER node
ENTRYPOINT ["node", "bin/veilus-mcp.js"]
