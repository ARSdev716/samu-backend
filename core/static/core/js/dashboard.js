// --- Tab Switching ---
function switchTab(tabId) {
    // Hide all views
    document.getElementById('view-supervision').classList.add('hidden');
    document.getElementById('view-supervision').classList.remove('flex');
    document.getElementById('view-historique').classList.add('hidden');
    document.getElementById('view-historique').classList.remove('flex');
    document.getElementById('view-flotte').classList.add('hidden');
    document.getElementById('view-flotte').classList.remove('flex');

    // Reset tabs UI
    ['supervision', 'historique', 'flotte'].forEach(t => {
        const el = document.getElementById('tab-' + t);
        el.className = "hover:text-slate-800 dark:hover:text-white transition-colors pt-5 pb-5 border-b-2 border-transparent hover:border-slate-300 dark:hover:border-slate-600";
    });

    // Show active view
    const view = document.getElementById('view-' + tabId);
    view.classList.remove('hidden');
    view.classList.add('flex');

    // Activate tab UI
    const activeEl = document.getElementById('tab-' + tabId);
    activeEl.className = "text-brand-blue border-b-2 border-brand-blue pb-5 pt-5 transition-colors";

    if (tabId === 'supervision') {
        map.invalidateSize();
    } else if (tabId === 'historique') {
        renderHistory();
    } else if (tabId === 'flotte') {
        renderFleet();
    }
}

// --- Theme & Clock ---
function toggleTheme() {
    document.documentElement.classList.toggle('dark');
}

function updateClock() {
    const now = new Date();
    document.getElementById('clock').innerText = now.toLocaleTimeString('fr-FR', {hour: '2-digit', minute:'2-digit', second:'2-digit'});
}
setInterval(updateClock, 1000);
updateClock();

// --- Map Init ---
const map = L.map('map', { zoomControl: false }).setView([3.8480, 11.5021], 13);
L.control.zoom({ position: 'bottomright' }).addTo(map);

L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}', {
    maxZoom: 19,
    attribution: '© Google Maps'
}).addTo(map);

// --- Custom Teardrop Pins ---
const createPin = (colorClass, iconFa, isPulse = false) => L.divIcon({
    html: '<div class="pin-wrapper ' + (isPulse ? 'pin-pulse' : '') + '"><div class="map-pin ' + colorClass + '"><i class="fas ' + iconFa + '"></i></div></div>',
    className: '', iconSize: [36, 36], iconAnchor: [18, 36], popupAnchor: [0, -36]
});

const iconSosNew = createPin('pin-red', 'fa-exclamation', true);
const iconSosCours = createPin('pin-orange', 'fa-spinner fa-spin');
const iconAmb = createPin('pin-blue', 'fa-truck-medical');
const iconHopital = createPin('pin-green', 'fa-hospital');

// --- State ---
let alertesData = [];
let ambulancesData = [];
let missionsData = [];
let hopitauxData = [];
let markers = {};
let selectedAlerteId = null;

// --- Data Fetching ---
async function fetchDashboardData() {
    try {
        const res = await fetch('/api/dashboard_data/');
        if (!res.ok) return;
        const data = await res.json();
        
        alertesData = data.alertes;
        ambulancesData = data.ambulances;
        missionsData = data.missions;
        hopitauxData = data.hopitaux;
        
        updateUI();
    } catch (err) {
        console.warn("Erreur API.");
    }
}

function updateUI() {
    // KPIs
    const nbNouveau = alertesData.filter(a => a.statut === 'en_attente').length;
    const nbCours = alertesData.filter(a => a.statut === 'en_cours' || a.statut === 'prise_en_charge').length;
    const nbDispo = ambulancesData.filter(a => a.statut === 'disponible').length;
    
    document.getElementById('kpi-sos').innerText = nbNouveau;
    document.getElementById('kpi-cours').innerText = nbCours;
    document.getElementById('kpi-amb').innerText = nbDispo;

    renderAlertList();

    // Map Markers
    Object.values(markers).forEach(m => map.removeLayer(m));
    markers = {};

    alertesData.forEach(a => {
        if(a.latitude) {
            const ic = a.statut === 'en_attente' ? iconSosNew : iconSosCours;
            const m = L.marker([a.latitude, a.longitude], {icon: ic}).addTo(map);
            m.bindPopup('<div class="font-semibold text-slate-800 dark:text-slate-200">SOS #' + a.id_suivi.substring(0,6).toUpperCase() + '</div><div class="text-slate-500 text-xs mt-1 capitalize">' + a.statut.replace('_', ' ') + '</div>');
            markers['sos_'+a.id] = m;
        }
    });

    ambulancesData.forEach(a => {
        if(a.latitude) {
            const m = L.marker([a.latitude, a.longitude], {icon: iconAmb}).addTo(map);
            m.bindPopup('<div class="font-semibold text-slate-800 dark:text-slate-200">Unité ' + a.immatriculation + '</div><div class="text-brand-blue text-xs mt-1 capitalize">' + a.statut + '</div>');
            markers['amb_'+a.id] = m;
        }
    });

    hopitauxData.forEach(h => {
        if(h.latitude) {
            const m = L.marker([h.latitude, h.longitude], {icon: iconHopital}).addTo(map);
            m.bindPopup('<div class="font-semibold text-slate-800 dark:text-slate-200">' + h.nom + '</div><div class="text-green-600 text-xs mt-1">Hôpital / Clinique</div>');
            markers['hop_'+h.id] = m;
        }
    });

    // Refresh dispatch panel if selected
    if (selectedAlerteId) {
        selectAlerte(selectedAlerteId, false);
    }
}

function renderAlertList() {
    const list = document.getElementById('alert-list');
    if(alertesData.length === 0) {
        list.innerHTML = '<div class="text-sm text-slate-400 p-6 text-center">Aucun incident actif.</div>';
        return;
    }

    let html = '';
    alertesData.forEach(a => {
        const isNew = a.statut === 'en_attente';
        const isSelected = selectedAlerteId === a.id;
        
        const bgClass = isSelected ? 'bg-blue-50 dark:bg-blue-900/20 border-brand-blue ring-1 ring-brand-blue' : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600';
        const iconColor = isNew ? 'text-brand-red bg-red-50 dark:bg-red-900/30' : 'text-brand-orange bg-orange-50 dark:bg-orange-900/30';
        const iconFa = isNew ? 'fa-exclamation-circle' : 'fa-spinner fa-spin';
        const timeStr = new Date(a.date_creation).toLocaleTimeString('fr-FR', {hour: '2-digit', minute:'2-digit'});

        html += `
            <div onclick="selectAlerte('${a.id}', true)" class="cursor-pointer p-3 rounded-lg border ${bgClass} transition-all">
                <div class="flex items-start gap-3">
                    <div class="w-8 h-8 rounded-full ${iconColor} flex items-center justify-center shrink-0 mt-0.5">
                        <i class="fas ${iconFa} text-sm"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="flex justify-between items-center mb-1">
                            <span class="font-bold text-slate-800 dark:text-white text-sm truncate">#${a.id_suivi.substring(0,8).toUpperCase()}</span>
                            <span class="text-xs text-slate-500 dark:text-slate-400 font-medium">${timeStr}</span>
                        </div>
                        <p class="text-xs text-slate-500 dark:text-slate-400 line-clamp-2 leading-relaxed">
                            ${a.adresse_manuelle || 'Coordonnées GPS'}
                        </p>
                    </div>
                </div>
            </div>
        `;
    });
    list.innerHTML = html;
}

function selectAlerte(id, pan = false) {
    const alerte = alertesData.find(a => a.id == id);
    if(!alerte) return;

    selectedAlerteId = id;
    if (pan && alerte.latitude) map.flyTo([alerte.latitude, alerte.longitude], 16, {duration: 1});

    document.getElementById('dispatch-empty').classList.add('hidden');
    document.getElementById('dispatch-active').classList.remove('hidden');
    
    document.getElementById('dispatch-id').innerText = '#' + alerte.id_suivi.substring(0,8).toUpperCase();
    document.getElementById('dispatch-loc').innerText = alerte.adresse_manuelle || 'Point GPS';

    const itineraire = document.getElementById('btn-itineraire');
    itineraire.href = "https://www.google.com/maps/dir/?api=1&destination=" + alerte.latitude + "," + alerte.longitude;

    if (alerte.statut === 'en_attente') {
        document.getElementById('dispatch-assignment').classList.remove('hidden');
        document.getElementById('mission-controls').classList.add('hidden');
        document.getElementById('mission-controls').classList.remove('flex');

        const select = document.getElementById('ambulance-select');
        select.innerHTML = '';
        const dispos = ambulancesData.filter(a => a.statut === 'disponible');
        if (dispos.length === 0) {
            select.innerHTML = '<option value="" disabled selected>Aucune unité disponible</option>';
        } else {
            dispos.forEach(amb => {
                select.innerHTML += '<option value="' + amb.id + '">' + amb.immatriculation + ' (' + amb.type_vehicule + ')</option>';
            });
        }
    } else {
        document.getElementById('dispatch-assignment').classList.add('hidden');
        document.getElementById('mission-controls').classList.remove('hidden');
        document.getElementById('mission-controls').classList.add('flex');

        const activeMission = missionsData.find(m => m.alerte == alerte.id && m.statut !== 'termine');
        if (activeMission) {
            document.getElementById('mission-status-select').value = activeMission.statut;
            document.getElementById('mission-status-select').dataset.missionId = activeMission.id;
        }
    }

    renderAlertList();
}

// --- Actions ---
async function deployerAmbulance() {
    if(!selectedAlerteId) return;
    const ambSelect = document.getElementById('ambulance-select');
    const ambId = ambSelect.value;
    
    if(!ambId) { alert("Aucune ambulance."); return; }
    const btn = document.getElementById('btn-deploy');
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> TRANSMISSION...';
    
    try {
        const res = await fetch('/api/missions/envoyer_dashboard/', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ alerte: selectedAlerteId, ambulance: ambId })
        });
        if(res.ok) {
            await fetchDashboardData();
        }
    } finally {
        btn.innerHTML = '<i class="fas fa-bolt"></i> <span class="tracking-wide">DÉCLENCHER L\'INTERVENTION</span>';
    }
}

async function updateMissionStatus() {
    const sel = document.getElementById('mission-status-select');
    const missionId = sel.dataset.missionId;
    const statut = sel.value;
    if(!missionId) return;

    try {
        const res = await fetch('/api/dashboard/mission/' + missionId + '/', {
            method: 'PATCH',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ statut: statut })
        });
        if(res.ok) {
            if (statut === 'termine') {
                selectedAlerteId = null;
                document.getElementById('dispatch-empty').classList.remove('hidden');
                document.getElementById('dispatch-active').classList.add('hidden');
            }
            await fetchDashboardData();
        }
    } catch(e) { console.error(e); }
}

// --- Victim Modal ---
function openVictimModal() {
    if(!selectedAlerteId) return;
    const alerte = alertesData.find(a => a.id == selectedAlerteId);
    if(alerte) {
        document.getElementById('victime-tel').value = alerte.telephone_victime || '';
        document.getElementById('victime-gravite').value = alerte.gravite || 'P2';
        document.getElementById('victime-desc').value = alerte.description || '';
        document.getElementById('modal-victime').classList.remove('hidden');
        document.getElementById('modal-victime').classList.add('flex');
    }
}

function closeVictimModal() {
    document.getElementById('modal-victime').classList.add('hidden');
    document.getElementById('modal-victime').classList.remove('flex');
}

async function saveVictimInfo() {
    if(!selectedAlerteId) return;
    const payload = {
        telephone_victime: document.getElementById('victime-tel').value,
        gravite: document.getElementById('victime-gravite').value,
        description: document.getElementById('victime-desc').value
    };

    try {
        const res = await fetch('/api/dashboard/alerte/' + selectedAlerteId + '/', {
            method: 'PATCH',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        if(res.ok) {
            closeVictimModal();
            fetchDashboardData();
        }
    } catch(e) { console.error(e); }
}

// --- History View ---
function renderHistory() {
    const tbody = document.getElementById('history-table-body');
    let html = '';
    missionsData.forEach(m => {
        const date = new Date(m.date_creation).toLocaleString('fr-FR', {dateStyle:'short', timeStyle:'short'});
        const sosId = m.alerte_detail ? m.alerte_detail.id_suivi.substring(0,8).toUpperCase() : '-';
        const gravite = m.alerte_detail ? m.alerte_detail.gravite : '-';
        const amb = m.ambulance_detail ? m.ambulance_detail.immatriculation : '-';
        const statusClass = m.statut === 'termine' ? 'text-green-600 bg-green-50 dark:bg-green-900/30 dark:text-green-400' : 'text-orange-600 bg-orange-50 dark:bg-orange-900/30 dark:text-orange-400';
        
        html += `
            <tr class="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                <td class="px-4 py-3 font-mono font-medium text-slate-800 dark:text-slate-200">#${m.id}</td>
                <td class="px-4 py-3">${date}</td>
                <td class="px-4 py-3 font-mono">#${sosId}</td>
                <td class="px-4 py-3 font-medium text-brand-blue">${amb}</td>
                <td class="px-4 py-3"><span class="px-2 py-1 rounded bg-slate-100 dark:bg-slate-700 font-medium text-xs">${gravite}</span></td>
                <td class="px-4 py-3"><span class="px-2 py-1 rounded text-xs font-semibold ${statusClass}">${m.statut}</span></td>
            </tr>
        `;
    });
    tbody.innerHTML = html;
}

// --- Fleet View ---
function renderFleet() {
    const grid = document.getElementById('fleet-grid');
    let html = '';
    ambulancesData.forEach(a => {
        const isDispo = a.statut === 'disponible';
        const statusColor = isDispo ? 'text-green-500' : 'text-orange-500';
        
        html += `
            <div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-5 flex flex-col gap-3">
                <div class="flex justify-between items-center border-b border-slate-100 dark:border-slate-700 pb-3">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-full bg-blue-50 dark:bg-blue-900/30 flex items-center justify-center text-brand-blue">
                            <i class="fas fa-ambulance"></i>
                        </div>
                        <div>
                            <p class="font-bold text-slate-800 dark:text-white leading-none">${a.immatriculation}</p>
                            <p class="text-xs text-slate-500 dark:text-slate-400 mt-1 uppercase">${a.type_vehicule}</p>
                        </div>
                    </div>
                    <div class="flex items-center gap-2">
                        <div class="w-2 h-2 rounded-full ${isDispo ? 'bg-green-500' : 'bg-orange-500'}"></div>
                        <span class="text-xs font-semibold capitalize ${statusColor}">${a.statut}</span>
                    </div>
                </div>
                <div class="text-sm text-slate-600 dark:text-slate-300">
                    <p><i class="fas fa-location-crosshairs w-5 text-slate-400"></i> ${a.latitude ? a.latitude.toFixed(4) + ', ' + a.longitude.toFixed(4) : 'Hors ligne'}</p>
                    <p class="mt-1"><i class="fas fa-gas-pump w-5 text-slate-400"></i> Niveau de carburant: 85%</p>
                </div>
            </div>
        `;
    });
    grid.innerHTML = html;
}

// Init
fetchDashboardData();
setInterval(fetchDashboardData, 3000);
