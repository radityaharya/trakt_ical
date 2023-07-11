# Trakt ICal

This is a simple script that will generate an ICal file for your Trakt.tv calendar to import into your calendar application of choice.or serve it through a Flask server to automatically import it into your Google Calendar.

Option 1: Hosted Solution
You can directly use the hosted version, which is accessible at https://trakt-ical.radityaharya.com/. This allows you to immediately benefit from the functionality without any additional setup requirements.

Option 2: Self-Hosting
Alternatively, if you prefer to host the application yourself, please follow the steps outlined below:

Set the following environment variables:

HOST: The base URL of the host.
MONGO_URL: MongoDB URL.
PORT: The port on which you will be hosting the application.
SECRET_KEY: A randomly generated string.
TRAKT_CLIENT_ID: Obtain this from https://trakt.tv/oauth/applications.
TRAKT_CLIENT_SECRET: Obtain this from https://trakt.tv/oauth/applications.
Ensure that the application is accessible to the internet as Google Calendar needs to access it for proper functionality.

Once you have hosted the application or accessed the provided link, it will automatically redirect for authentication with Trakt. Following successful authentication, you will obtain your ICal URL.
