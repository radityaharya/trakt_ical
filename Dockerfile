FROM python:3.9
ADD . /trakt_ical
WORKDIR /trakt_ical
RUN pip install -r requirements.txt
EXPOSE 8000
CMD ["python", "trakt_ical", "--serve"]