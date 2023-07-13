const MAX_DAYS = 30;

function editUrl() {
  const url = window.location.href;
  var base_url = url.substring(0, url.lastIndexOf("/"));
  var key = url.substring(url.lastIndexOf("=") + 1);
  
  var days_ago = document.getElementById("days_ago").value;
  var days = document.getElementById("days").value;

  var days_ago = parseInt(days_ago);
  var days = parseInt(days);
          
  var newurl = new URL(base_url);
  newurl = newurl.toString();
  newurl = newurl.split("?")[0];
  
  var params = new URLSearchParams();
  
  params.append("key", key);
  params.append("days_ago", days_ago);
  params.append("period", days);
  
  const final_url = `${newurl}?${params.toString()}`;
  
  document.getElementById("url").innerHTML = `<a href="${final_url}">${final_url}</a>`;
}

function estimate(){
  var days_ago = document.getElementById("days_ago").value;
  var days_ahead = document.getElementById("days").value;
  
  var days_ago = parseInt(days_ago);
  var days_ahead = parseInt(days_ahead);

  var today = new Date();
  var today = today.getTime();

  var days_ago = days_ago * 86400000;
  var days_ahead = days_ahead * 86400000;

  var start = new Date(today - days_ago).toISOString().split("T")[0];
  var end = new Date(today + days_ahead).toISOString().split("T")[0];

  const total = (days_ago + days_ahead) / 86400000;

  const estimated = document.getElementById("estimated_time");

  estimated.innerHTML = `This will fetch data from ${start} to ${end} with a total of ${total} days.`;
}

function addGoogle() {
  const url = window.location.href;
  var base_url = url.substring(0, url.lastIndexOf("/"));
  var key = url.substring(url.lastIndexOf("=") + 1);
  
  var days_ago = document.getElementById("days_ago").value;
  var days = document.getElementById("days").value;
          
  var newurl = new URL(base_url);
  newurl = newurl.toString();
  newurl = newurl.split("?")[0];
  
  var params = new URLSearchParams();
  
  params.append("key", key);
  params.append("days_ago", days_ago);
  params.append("period", days);
  
  const final_url = `${newurl}?${params.toString()}`;
  
  var webcal_url = final_url.replace("https://", "webcal://");
  
  var gcalurl = "https://calendar.google.com/calendar/render?cid=" + encodeURIComponent(webcal_url);
  
  window.open(gcalurl, "_blank");
}

function copyUrl() {
  var url = document.getElementById("url").innerText;
  navigator.clipboard.writeText(url);
}

async function renderPreviewTable(){
  var table = document.getElementById("preview");
  
  const url = window.location.href;
  var base_url = url.substring(0, url.lastIndexOf("/"));
  var key = url.substring(url.lastIndexOf("=") + 1);
  
  var days_ago = document.getElementById("days_ago").value;
  var days = document.getElementById("days").value;
          
  var newurl = new URL(base_url);
  newurl = newurl.toString();
  newurl = newurl.split("?")[0];
  
  var params = new URLSearchParams();
  
  params.append("key", key);
  params.append("days_ago", days_ago);
  params.append("period", days);
  
  const final_url = `${newurl}preview?${params.toString()}`;
  
  table.innerHTML = "";
  
  tablehead = table.appendChild(document.createElement("thead"));
  tablebody = table.appendChild(document.createElement("tbody"));
  
  tablehead.innerHTML = `
      <tr>
          <th>Show</th>
          <th>Season</th>
          <th>Episode</th>
          <th>Title</th>
          <th>Overview</th>
          <th>Air date</th>
      </tr>
  `;
  
  const response = await fetch(final_url);
  const data = await response.json();
  
  console.log(data);
  
  tablebody.innerHTML = data.map(item => `
      <tr>
          <td>${item.show}</td>
          <td>${item.season}</td>
          <td>${item.number}</td>
          <td>${item.title}</td>
          <td>${item.overview}</td>
          <td>${item.airs_at}</td>
      </tr>
  `).join("");
}

function actions(){
  editUrl();
  estimate();
  renderPreviewTable()
}

actions();