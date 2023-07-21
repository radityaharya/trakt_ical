FROM nikolaik/python-nodejs:latest
ADD . /trakt_ical
WORKDIR /trakt_ical
RUN pip install -r requirements.txt
EXPOSE 8000

WORKDIR /trakt_ical/trakt_ical/frontend
RUN npm i && npm run build

WORKDIR /trakt_ical/trakt_ical

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "serve_ical:app"]