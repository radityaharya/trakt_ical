FROM nikolaik/python-nodejs:latest
ADD . /trakt_ical
WORKDIR /trakt_ical
RUN pip install -r requirements.txt
EXPOSE 8000

WORKDIR /trakt_ical/trakt_ical/frontend
RUN npm i && npm run build

WORKDIR /trakt_ical

CMD ["python", "trakt_ical", "--serve"]