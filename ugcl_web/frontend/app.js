let map;
let rf1Layer = null;
let rf2Layer = null;
let changeLayer = null;
let layerControl = null;
let baseOSM = null;

async function fetchYears() {
  const res = await fetch("/api/years");
  const data = await res.json();
  return data.years || [];
}

function setDropdownOptions(el, years) {
  el.innerHTML = "";
  years.forEach(y => {
    const opt = document.createElement("option");
    opt.value = String(y);
    opt.textContent = String(y);
    el.appendChild(opt);
  });
}

function initMap() {
  map = L.map("map").setView([6.9271, 79.8612], 11);

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

async function postJson(url, payload) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail || data.error || "Request failed");
  }

  return data;
}

async function loadStats(y1, y2) {
  const res = await fetch(`/api/stats?y1=${y1}&y2=${y2}`);
  const data = await res.json();

  if (data.error) {
    document.getElementById("stats").innerHTML = `<div style="color:red;">${data.error}</div>`;
    return;
  }

  document.getElementById("stats").innerHTML = `
    <div><b>Vegetation ${y1}:</b> ${data.veg_y1_ha} ha</div>
    <div><b>Vegetation ${y2}:</b> ${data.veg_y2_ha} ha</div>
    <div><b>Net Change:</b> ${data.net_change_ha} ha</div>
    <div><b>Net Change (%):</b> ${data.net_change_percent}%</div>
  `;
}

async function loadLayers() {
  const y1 = document.getElementById("y1").value;
  const y2 = document.getElementById("y2").value;

  if (!y1 || !y2) {
    alert("Please select Year 1 and Year 2.");
    return;
  }

  if (layerControl) map.removeControl(layerControl);
  if (rf1Layer) map.removeLayer(rf1Layer);
  if (rf2Layer) map.removeLayer(rf2Layer);
  if (changeLayer) map.removeLayer(changeLayer);

  // check if rf exists
  const rf1Status = await fetch(`/api/file-status?year=${y1}`).then(r => r.json());
  const rf2Status = await fetch(`/api/file-status?year=${y2}`).then(r => r.json());
  const chgStatus = await fetch(`/api/change-status?y1=${y1}&y2=${y2}`).then(r => r.json());

  const overlays = {};

  if (rf1Status.rf_exists) {
    rf1Layer = buildRfLayer(y1);
    rf1Layer.addTo(map);
    overlays[`RF ${y1}`] = rf1Layer;
  }

  if (rf2Status.rf_exists) {
    rf2Layer = buildRfLayer(y2);
    rf2Layer.addTo(map);
    overlays[`RF ${y2}`] = rf2Layer;
  }

  if (chgStatus.change_exists) {
    changeLayer = buildChangeLayer(y1, y2);
    changeLayer.addTo(map);
    overlays[`Change ${y1} → ${y2}`] = changeLayer;
  }

  layerControl = L.control.layers({ "OSM": baseOSM }, overlays).addTo(map);

  await loadStats(y1, y2);
}

async function runRf() {
  const year = document.getElementById("y1").value;

  if (!year) {
    alert("Please select a year first.");
    return;
  }

  try {
    const result = await postJson("/api/run/rf", {
      year: parseInt(year)
    });

    alert(`RF processing completed.\nStatus: ${result.status}\nMessage: ${result.message}`);
    await loadLayers();
  } catch (err) {
    console.error(err);
    alert("RF generation failed: " + err.message);
  }
}

async function runChange() {
  const y1 = document.getElementById("y1").value;
  const y2 = document.getElementById("y2").value;

  if (!y1 || !y2) {
    alert("Please select both years.");
    return;
  }

  if (y1 === y2) {
    alert("Please select two different years.");
    return;
  }

  try {
    const result = await postJson("/api/run/change", {
      y1: parseInt(y1),
      y2: parseInt(y2)
    });

    alert(`Change detection completed.\nStatus: ${result.status}\nMessage: ${result.message}`);
    await loadLayers();
  } catch (err) {
    console.error(err);
    alert("Change detection failed: " + err.message);
  }
}

async function main() {
  initMap();

  const years = await fetchYears();
  const y1El = document.getElementById("y1");
  const y2El = document.getElementById("y2");

  setDropdownOptions(y1El, years);
  setDropdownOptions(y2El, years);

  y1El.value = String(years[0]);
  y2El.value = String(years[years.length - 1]);

  document.getElementById("btnLoad").addEventListener("click", loadLayers);
  document.getElementById("btnRF").addEventListener("click", runRf);
  document.getElementById("btnChange").addEventListener("click", runChange);

  await loadLayers();
}

window.addEventListener("DOMContentLoaded", main);