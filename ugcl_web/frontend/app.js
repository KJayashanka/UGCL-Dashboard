let map;
let rf1Layer, rf2Layer, changeLayer;
let baseOSM;

async function fetchYears() {
  const res = await fetch("/api/years");
  const data = await res.json();
  return data.years || [];
}

function setDropdownOptions(el, years) {
  el.innerHTML = "";
  years.forEach(y => {
    const opt = document.createElement("option");
    opt.value = y;
    opt.textContent = y;
    el.appendChild(opt);
  });
}

function initMap() {
  map = L.map("map").setView([6.9271, 79.8612], 11); // Colombo approx
  baseOSM = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "© OpenStreetMap"
  }).addTo(map);
}

function buildRfLayer(year) {
  return L.tileLayer(`/tiles/rf/${year}/{z}/{x}/{y}.png`, { opacity: 0.75 });
}

function buildChangeLayer(y1, y2) {
  return L.tileLayer(`/tiles/change/${y1}/${y2}/{z}/{x}/{y}.png`, { opacity: 0.75 });
}

async function loadStats(y1, y2) {
  const res = await fetch(`/api/stats?y1=${y1}&y2=${y2}`);
  const data = await res.json();

  if (data.error) {
    document.getElementById("stats").innerText = data.error;
    return;
  }

  document.getElementById("stats").innerHTML = `
    <div><b>Vegetation ${y1}:</b> ${data.veg_y1_ha} ha</div>
    <div><b>Vegetation ${y2}:</b> ${data.veg_y2_ha} ha</div>
    <div><b>Net Change:</b> ${data.net_change_ha} ha (${data.net_change_percent}%)</div>
  `;
}

async function loadLayers() {
  const y1 = document.getElementById("y1").value;
  const y2 = document.getElementById("y2").value;

  if (rf1Layer) map.removeLayer(rf1Layer);
  if (rf2Layer) map.removeLayer(rf2Layer);
  if (changeLayer) map.removeLayer(changeLayer);

  rf1Layer = buildRfLayer(y1).addTo(map);
  rf2Layer = buildRfLayer(y2).addTo(map);
  changeLayer = buildChangeLayer(y1, y2).addTo(map);

  const overlays = {
    [`RF ${y1}`]: rf1Layer,
    [`RF ${y2}`]: rf2Layer,
    [`Change ${y1}→${y2}`]: changeLayer
  };

  L.control.layers({ "OSM": baseOSM }, overlays).addTo(map);

  await loadStats(y1, y2);
}

async function postJson(url, params) {
  const q = new URLSearchParams(params).toString();
  const res = await fetch(`${url}?${q}`, { method: "POST" });
  return await res.json();
}

async function runRf() {
  const y1 = document.getElementById("y1").value;

  if (!y1) {
    alert("Please select a year before running RF classification.");
    return;
  }

  const r = await postJson("/api/run/rf", { year: y1 });
  alert(`RF job status: ${r.status}\n${r.message}`);
}

async function runChange() {
  const y1 = document.getElementById("y1").value;
  const y2 = document.getElementById("y2").value;
  const r = await postJson("/api/run/change", { y1, y2 });
  alert(`Change job status: ${r.status}\n${r.message}`);
}

async function main() {
  initMap();

  const years = await fetchYears();
  const y1El = document.getElementById("y1");
  const y2El = document.getElementById("y2");

  if (!years || years.length === 0) {
    alert("No available years found. Please make sure rf_YYYY.tif files exist in outputs/maps.");
    return;
  }

  setDropdownOptions(y1El, years);
  setDropdownOptions(y2El, years);

  y1El.value = String(years[0]);
  y2El.value = String(years[years.length - 1]);

  document.getElementById("btnLoad").onclick = loadLayers;
  document.getElementById("btnRF").onclick = runRf;
  document.getElementById("btnChange").onclick = runChange;

  await loadLayers();
}

main();