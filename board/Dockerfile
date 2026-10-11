FROM python:3.12-alpine
WORKDIR /app
COPY places.py server.py index.html ./
ENV PORT=8787
EXPOSE 8787
USER nobody
CMD ["python3", "server.py"]
