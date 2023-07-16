# Trakt ICal

Trakt ICal is a script that generates an ICal file for your Trakt.tv calendar, which you can import into your calendar application or serve through a Flask server to automatically import it into your Google Calendar. This readme provides instructions on how to set up and use Trakt ICal.

## Prerequisites

Before setting up Trakt ICal, ensure that you have the following prerequisites installed:

- Python (version 3.6 or higher)
- MongoDB (if self-hosting)

## Option 1: Hosted Solution

You can directly use the hosted version of Trakt ICal, which is accessible at [https://trakt-ical.radityaharya.com/](https://trakt-ical.radityaharya.com/). Simply visit the provided URL and follow the authentication process to obtain your ICal URL.

## Option 2: Self-Hosting

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/00A3Nv?referralCode=radityaharya)

If you prefer to host the application yourself, follow the steps below:

1. Set up the environment:

   - Install the required Python dependencies by running the following command:

     ```
     pip install -r requirements.txt
     ```

   - If you haven't already, install MongoDB following the instructions for your operating system from the official MongoDB documentation: [https://docs.mongodb.com/manual/installation/](https://docs.mongodb.com/manual/installation/)

2. Set the following environment variables:

   - `HOST`: The base URL of the host.
   - `MONGO_URL`: MongoDB URL (e.g., `mongodb://localhost:27017/`).
   - `PORT`: The port on which you will be hosting the application.
   - `TRAKT_CLIENT_ID`: Obtain this from [https://trakt.tv/oauth/applications](https://trakt.tv/oauth/applications).
   - `TRAKT_CLIENT_SECRET`: Obtain this from [https://trakt.tv/oauth/applications](https://trakt.tv/oauth/applications).

3. Ensure that the application is accessible to the internet, as Google Calendar needs to access it for proper functionality.

4. Run the application:

   - For the Flask development server, execute the following command:

     ```bash
     python serve_ical.py
     ```

   - For production deployment, consider using a production-ready web server, such as Gunicorn or uWSGI. Refer to the Flask documentation for instructions on deploying Flask applications in production. You can use services such as [Railway](https://railway.app/) or [Fly.io](https://fly.io/) to host the application.

5. Once you have hosted the application or accessed the provided link, it will automatically redirect you for authentication with Trakt. After successful authentication, you will obtain your ICal URL.

## Usage

After setting up Trakt ICal, you can use the generated ICal URL to import your Trakt.tv calendar into your preferred calendar application. The specific steps to import the ICal file vary depending on the application you are using. The landing page provides instructions for importing the ICal file into Google Calendar and Outlook Calendar.

```
disclaimer: This project is not affiliated with Trakt.tv in any way. It is a personal project that I created for my own use, and I decided to make it public in case anyone else finds it useful. If you have any questions or suggestions, feel free to open an issue or contact me on [contact@radityaharya.com](mailto:contact@radityaharya.com) or create an issue on GitHub.
```