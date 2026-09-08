FROM nginx:alpine

LABEL "Project"="EmeraldFlow"
LABEL "Author"="EmeraldFlow Team"

RUN rm -rf /etc/nginx/conf.d/default.conf
COPY nginx-emeraldapp.conf /etc/nginx/conf.d/emeraldapp.conf