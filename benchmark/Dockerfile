FROM alpine:latest

RUN apk add --no-cache apache2-utils

WORKDIR /benchmark

COPY run_benchmark.sh .

CMD ["sh", "run_benchmark.sh"]
