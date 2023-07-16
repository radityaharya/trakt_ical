const MAX_DAYS = 30;

function getCalendarType() {
  return document.getElementById("calendar_type").value;
}

function getUrlParams() {
  const url = window.location.href;
  const base_url = url.substring(0, url.lastIndexOf("/"));
  const key = url.substring(url.lastIndexOf("=") + 1);
  const days_ago = parseInt(document.getElementById("days_ago").value);
  const days = parseInt(document.getElementById("days").value);

  const newurl = new URL(base_url);
  const params = new URLSearchParams();

  params.append("key", key);
  params.append("days_ago", days_ago);
  params.append("period", days);

  const final_url = `${newurl}${getCalendarType()}?${params.toString()}`;

  return { final_url, key, days_ago, days };
}

function editUrl() {
  const { final_url } = getUrlParams();

  document.getElementById("url").innerHTML = `<a href="${final_url}">${final_url}</a>`;
}

function estimate() {
  const { days_ago, days } = getUrlParams();

  const today = new Date().getTime();
  const days_ago_ms = days_ago * 86400000;
  const days_ahead_ms = days * 86400000;

  const start = new Date(today - days_ago_ms).toISOString().split("T")[0];
  const end = new Date(today + days_ahead_ms).toISOString().split("T")[0];

  const total = (days_ago_ms + days_ahead_ms) / 86400000;

  const estimated = document.getElementById("estimated_time");

  estimated.innerHTML = `This will fetch data from ${start} to ${end} with a total of ${total} days.`;
}

function addCalendarProtocol(protocol) {
  const { final_url } = getUrlParams();
  const webcal_url = final_url.replace("https://", "webcal://").replace("http://", "webcal://");

  let calendarUrl;

  switch (protocol) {
    case "webcal":
      calendarUrl = webcal_url;
      break;
    case "google":
      calendarUrl = `https://calendar.google.com/calendar/render?cid=${encodeURIComponent(webcal_url)}`;
      break;
    case "outlook365":
      calendarUrl = `https://outlook.office.com/owa?path=%2Fcalendar%2Faction%2Fcompose&rru=addsubscription&url=${encodeURIComponent(webcal_url)}&name=Trakt%20iCal`;
      break;
    case "outlooklive":
      calendarUrl = `https://outlook.live.com/owa?path=%2Fcalendar%2Faction%2Fcompose&rru=addsubscription&url=${encodeURIComponent(webcal_url)}&name=Trakt%20iCal`;
      break;
  }

  window.open(calendarUrl, "_blank");
}

function copyUrl() {
  const url = document.getElementById("url").innerText;
  navigator.clipboard.writeText(url);
}

async function fetchPreviewData() {
  const { final_url, key, days_ago, days } = getUrlParams();

  var base_url = final_url.substring(0, final_url.lastIndexOf("?"));
  var json_url = `${base_url}/json?${final_url.substring(final_url.lastIndexOf("?") + 1)}`;
  
  json_url += `&key=${key}&days_ago=${days_ago}&period=${days}`;
  
  const response = await fetch(json_url);
  const data = await response.json();
  return data;
}

async function renderPreviewTable() {
  const table = document.getElementById("preview");

  table.innerHTML = "";
  const tablehead = table.appendChild(document.createElement("thead"));
  const tablebody = table.appendChild(document.createElement("tbody"));

  switch (getCalendarType()) {
    case "shows":
      tablehead.innerHTML = `
        <tr>
            <th>Show</th>
            <th>Season</th>
            <th>Episode</th>
            <th>Title</th>
            <th>Overview</th>
            <th>Airs At</th>
            <th>Runtime (min)</th>
        </tr>
      `;

      const data = await fetchPreviewData();

      console.log(data);

      tablebody.innerHTML = data.map(
        (item) => `
          <tr>
              <td>${item.show}</td>
              <td>${item.season}</td>
              <td>${item.number}</td>
              <td>${item.title}</td>
              <td>${item.overview}</td>
              <td>${new Date(item.airs_at).toLocaleString()}</td>
              <td>${item.runtime}</td>
          </tr>
      `
      ).join("");
      break;

    case "movies":
      tablehead.innerHTML = `
        <tr>
            <th>Movie</th>
            <th>Overview</th>
            <th>Released</th>
            <th>Runtime (min)</th>
        </tr>
      `;

      const data2 = await fetchPreviewData();

      console.log(data2);

      tablebody.innerHTML = data2.map(
        (item) => `
          <tr>
              <td>${item.title}</td>
              <td>${item.overview}</td>
              <td>${new Date(item.released).toLocaleString()}</td>
              <td>${item.runtime}</td>
          </tr>
      `
      ).join("");
      break;
  }
}

function actions() {
  editUrl();
  estimate();
  renderPreviewTable();
}

actions();
