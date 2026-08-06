# One-shot container: pulls the Ollama model with progress, then exits.
# Runs alongside api/web on every `docker compose up`; nothing else depends on
# it finishing, so a slow model download never blocks the rest of the stack.
FROM alpine:3.20

RUN apk add --no-cache curl bash

COPY pull-model.sh /pull-model.sh
RUN chmod +x /pull-model.sh

ENTRYPOINT ["/pull-model.sh"]
