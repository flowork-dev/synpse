document.addEventListener("DOMContentLoaded", function() {
    // --- CACHE DOM ELEMENTS ---
    const kernelVersionSpan = document.getElementById('kernel-version');
    const licenseTierSpan = document.getElementById('license-tier');
    const kernelUptimeSpan = document.getElementById('kernel-uptime');
    const cpuLoadSpan = document.getElementById('cpu-load');
    const ramUsageSpan = document.getElementById('ram-usage');
    const accessUrlLink = document.getElementById('access-url');
    const copyIpButton = document.getElementById('copy-ip-button');
    const apiStatusSpan = document.getElementById('api-status');
    const gatewayStatusSpan = document.getElementById('gateway-status');
    const reconnectGatewayBtn = document.getElementById('reconnect-gateway-btn');
    const engineTokenField = document.getElementById('engine-token-field');
    const copyTokenButton = document.getElementById('copy-token-button');
    const logContainer = document.getElementById('log-container');
    const specOsSpan = document.getElementById('spec-os');
    const specArchSpan = document.getElementById('spec-arch');
    const specProcSpan = document.getElementById('spec-proc');
    const specCpuSpan = document.getElementById('spec-cpu');
    const specRamSpan = document.getElementById('spec-ram');
    const specGpuContainer = document.getElementById('spec-gpu-container');
    // (PENAMBAHAN KODE) Cache tombol baru
    const authViaGatewayBtn = document.getElementById('auth-via-gateway-btn');


    // --- REAL-TIME LOGS WITH SOCKET.IO ---
    const socket = io('/dashboard_events');

    socket.on('connect', () => {
        console.log('Successfully connected to dashboard WebSocket.');
        appendLog({ level: 'SUCCESS', source: 'Dashboard', message: 'Real-time log stream connected.' });
    });

    socket.on('new_log', (log) => {
        appendLog(log);
    });

    function appendLog(log) {
        const shouldScroll = logContainer.scrollTop + logContainer.clientHeight >= logContainer.scrollHeight - 20;
        const p = document.createElement('p');
        p.className = `log-entry log-${log.level.toLowerCase()}`;
        p.textContent = `[${log.level}] ${log.source ? '[' + log.source + ']' : ''} > ${log.message}`;
        logContainer.appendChild(p);
        if (shouldScroll) {
            logContainer.scrollTop = logContainer.scrollHeight;
        }
    }


    // --- API CALLS & DATA UPDATES ---
    async function updateVitals() {
        try {
            const response = await fetch('/api/vitals');
            const data = await response.json();
            kernelVersionSpan.textContent = data.kernel_version;
            licenseTierSpan.textContent = data.license_tier;
            kernelUptimeSpan.textContent = formatUptime(data.uptime_seconds);
            cpuLoadSpan.textContent = data.cpu_percent.toFixed(1);
            // (PERBAIKAN KUNCI) Mengganti data.ram_gb menjadi data.ram_mb agar cocok dengan backend
            ramUsageSpan.textContent = data.ram_mb.toFixed(2);
        } catch (error) {
            console.error("Failed to fetch vitals:", error);
        }
    }

    async function updateServerInfo() {
        try {
            const response = await fetch('/api/server_info');
            const data = await response.json();
            accessUrlLink.textContent = `http://${data.local_ip}:${data.dashboard_port}`;
            accessUrlLink.href = `http://${data.local_ip}:${data.dashboard_port}`;
            apiStatusSpan.textContent = data.api_server.status;
            gatewayStatusSpan.textContent = data.gateway_status;
        } catch (error) {
            console.error("Failed to fetch server info:", error);
        }
    }

    async function updateSystemSpecs() {
        try {
            const response = await fetch('/api/system_specs');
            const data = await response.json();
            specOsSpan.textContent = data.os;
            specArchSpan.textContent = data.architecture;
            specProcSpan.textContent = data.processor;
            specCpuSpan.textContent = `${data.cpu_cores} Cores, ${data.cpu_threads} Threads`;
            specRamSpan.textContent = data.ram_total_gb;
            engineTokenField.value = data.engine_token;

            if (data.gpus && Array.isArray(data.gpus)) {
                specGpuContainer.innerHTML = data.gpus.map(gpu =>
                    `<p class="mb-1"><strong>GPU:</strong> ${gpu.name} (${gpu.memory_total_mb} MB)</p>`
                ).join('');
            } else {
                specGpuContainer.innerHTML = `<p class="mb-1"><strong>GPU:</strong> ${data.gpus}</p>`;
            }
        } catch (error) {
            console.error("Failed to fetch system specs:", error);
        }
    }

    // --- EVENT LISTENERS ---
    copyIpButton.addEventListener('click', () => {
        navigator.clipboard.writeText(accessUrlLink.href);
    });

    function showCopySuccess(buttonElement) {
        const originalIcon = buttonElement.innerHTML;
        buttonElement.innerHTML = `<i class="bi bi-check-lg text-success"></i>`;
        setTimeout(() => {
            buttonElement.innerHTML = originalIcon;
        }, 2000);
    }

    function fallbackCopyTextToClipboard(text, inputElement, buttonElement) {
        inputElement.select();
        try {
            var successful = document.execCommand('copy');
            if (successful) {
                showCopySuccess(buttonElement);
            } else {
                 throw new Error('Fallback copy command failed');
            }
        } catch (err) {
            console.error('Fallback copy was unsuccessful:', err);
            const originalIcon = buttonElement.innerHTML;
            buttonElement.innerHTML = `<i class="bi bi-x-lg text-danger"></i>`;
             setTimeout(() => {
                buttonElement.innerHTML = originalIcon;
            }, 2000);
        }
        window.getSelection().removeAllRanges();
    }

    copyTokenButton.addEventListener('click', () => {
        const token = engineTokenField.value;
        if (!token || token.includes('...')) return;

        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(token).then(() => {
                showCopySuccess(copyTokenButton);
            }).catch(err => {
                fallbackCopyTextToClipboard(token, engineTokenField, copyTokenButton);
            });
        } else {
            fallbackCopyTextToClipboard(token, engineTokenField, copyTokenButton);
        }
    });

    reconnectGatewayBtn.addEventListener('click', async () => {
        reconnectGatewayBtn.disabled = true;
        reconnectGatewayBtn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Reconnecting...`;
        try {
            await fetch('/api/actions/reconnect_gateway', { method: 'POST' });
            setTimeout(updateServerInfo, 1000);
        } finally {
            setTimeout(() => {
                reconnectGatewayBtn.disabled = false;
                reconnectGatewayBtn.innerHTML = `<i class="bi bi-arrow-repeat me-1"></i> Force Reconnect to Gateway`;
            }, 3000);
        }
    });

    // (PENAMBAHAN KODE) Event listener untuk tombol otentikasi baru
    authViaGatewayBtn.addEventListener('click', async () => {
        authViaGatewayBtn.disabled = true;
        authViaGatewayBtn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Waiting...`;

        try {
            const response = await fetch('/api/auth/initiate', { method: 'POST' });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error);

            // Buka jendela popup ke Gateway
            const authWindow = window.open(data.redirect_url, 'FloworkAuth', 'width=600,height=700');

            // Mulai polling untuk cek status
            const pollInterval = setInterval(async () => {
                const statusResponse = await fetch(`/api/auth/status/${data.request_id}`);
                const statusData = await statusResponse.json();

                if (statusData.status === 'success') {
                    clearInterval(pollInterval);
                    if (authWindow) authWindow.close();
                    appendLog({level: 'SUCCESS', source: 'Auth', message: 'Token successfully synced from Gateway!'});
                    // Refresh semua data setelah token baru diterima
                    updateSystemSpecs();
                    updateServerInfo();
                    authViaGatewayBtn.innerHTML = `<i class="bi bi-check-circle-fill me-2"></i> Synced!`;
                     setTimeout(() => {
                        authViaGatewayBtn.disabled = false;
                        authViaGatewayBtn.innerHTML = `<i class="bi bi-box-arrow-in-right me-2"></i> Connect Account & Get Token`;
                    }, 4000);
                } else if (statusData.status === 'not_found' || statusData.status === 'expired') {
                    clearInterval(pollInterval);
                    appendLog({level: 'ERROR', source: 'Auth', message: 'Auth request expired or was invalid.'});
                    authViaGatewayBtn.disabled = false;
                    authViaGatewayBtn.innerHTML = `<i class="bi bi-box-arrow-in-right me-2"></i> Connect Account & Get Token`;
                }

                // Cek apakah jendela popup ditutup manual oleh user
                if (authWindow && authWindow.closed && statusData.status === 'pending') {
                    clearInterval(pollInterval);
                    appendLog({level: 'WARN', source: 'Auth', message: 'Authentication cancelled by user.'});
                    authViaGatewayBtn.disabled = false;
                    authViaGatewayBtn.innerHTML = `<i class="bi bi-box-arrow-in-right me-2"></i> Connect Account & Get Token`;
                }

            }, 3000); // Cek setiap 3 detik

        } catch(error) {
            appendLog({level: 'ERROR', source: 'Auth', message: `Failed to initiate auth: ${error.message}`});
            authViaGatewayBtn.disabled = false;
            authViaGatewayBtn.innerHTML = `<i class="bi bi-box-arrow-in-right me-2"></i> Connect Account & Get Token`;
        }
    });

    // --- UTILITY FUNCTIONS ---
    function formatUptime(seconds) {
        const d = Math.floor(seconds / (3600*24));
        const h = Math.floor(seconds % (3600*24) / 3600);
        const m = Math.floor(seconds % 3600 / 60);
        const s = Math.floor(seconds % 60);

        const dDisplay = d > 0 ? d + (d == 1 ? " day, " : " days, ") : "";
        const hDisplay = h > 0 ? h + (h == 1 ? " hr, " : " hrs, ") : "";
        const mDisplay = m > 0 ? m + (m == 1 ? " min, " : " mins, ") : "";
        const sDisplay = s > 0 ? s + (s == 1 ? " sec" : " secs") : "";
        return dDisplay + hDisplay + mDisplay + sDisplay;
    }


    // --- INITIALIZATION ---
    updateVitals();
    updateServerInfo();
    updateSystemSpecs();
    setInterval(updateVitals, 2000);
    setInterval(updateServerInfo, 5000);
});