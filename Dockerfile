FROM node:22-bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip ffmpeg libraqm0 libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
RUN pip3 install --no-cache-dir --break-system-packages numpy pillow opencv-python-headless
WORKDIR /app
COPY package.json ./
RUN npm install --omit=dev
COPY . .
ENV NODE_ENV=production DATA_DIR=/data PORT=3000
EXPOSE 3000
CMD ["node", "--disable-warning=ExperimentalWarning", "server.js"]
