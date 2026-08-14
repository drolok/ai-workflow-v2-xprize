FROM node:20-alpine AS base
ENV PNPM_HOME=/pnpm
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable && corepack prepare pnpm@9.15.0 --activate

WORKDIR /app
COPY package.json pnpm-workspace.yaml ./
COPY apps/api/package.json ./apps/api/package.json
COPY apps/api/tsconfig.json ./apps/api/tsconfig.json
COPY apps/api/src ./apps/api/src
COPY packages ./packages

RUN pnpm install --frozen-lockfile --ignore-scripts
RUN pnpm --filter api build

FROM node:20-alpine AS runtime
ENV NODE_ENV=production PORT=3001
WORKDIR /app
COPY --from=base /app/apps/api/package.json ./apps/api/package.json
COPY --from=base /app/apps/api/dist ./apps/api/dist
COPY --from=base /app/node_modules ./node_modules
EXPOSE 3001
CMD ["node", "apps/api/dist/index.js"]
