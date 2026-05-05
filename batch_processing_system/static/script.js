let currentLogs = [];
let volumeChart, successChart;

// Immediate Theme Initialization (Fail-safe)
(function() {
    try {
        const theme = localStorage.getItem('theme') || 'dark';
        if (theme === 'light') {
            document.documentElement.classList.add('light-theme');
            // We'll also apply to body in DOMContentLoaded to be sure
        }
    } catch (e) { console.warn("Theme persistence blocked"); }
})();

document.addEventListener('DOMContentLoaded', () => {
    console.log("System Initializing...");
    
    // Sync body with theme state
    if (document.documentElement.classList.contains('light-theme')) {
        document.body.classList.add('light-theme');
        const themeBtn = document.getElementById('theme-toggle');
        if (themeBtn) themeBtn.innerText = '🌙';
    } else {
        const themeBtn = document.getElementById('theme-toggle');
        if (themeBtn) themeBtn.innerText = '☀️';
    }

    initTabs();
    initControls();
    initCharts();
    fetchData();
    
    // Fast polling while jobs are running, slower otherwise
    setInterval(() => {
        const isRunning = currentLogs.some(l => l.status === 'Running');
        if (isRunning) {
            fetchData();
        }
    }, 2000); // Poll every 2s if something is running

    // Base background refresh every 10s
    setInterval(fetchData, 10000);
});

function initTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            const target = document.getElementById(`${tabId}-tab`);
            if (target) target.classList.add('active');
            
            if (tabId === 'scheduler') fetchScheduledJobs();
            if (tabId === 'monitoring') fetchJobLogs();
            if (tabId === 'dashboard') fetchReports();
        });
    });
}

function initControls() {
    const triggerBtn = document.getElementById('trigger-btn');
    if (triggerBtn) {
        triggerBtn.onclick = async () => {
            const dateInput = document.getElementById('job-date');
            if (!dateInput || !dateInput.value) return showToast('Please select a date', 'error');
            
            triggerBtn.disabled = true;
            try {
                const response = await fetch(`/trigger_job/${dateInput.value}`, { method: 'POST' });
                if (response.ok) {
                    showToast('Batch job queued (3 Workers assigned)', 'success');
                    // Immediate refresh to show "Running" state
                    await fetchData();
                } else {
                    showToast('Failed to trigger job', 'error');
                }
            } catch (e) {
                showToast('Network error', 'error');
            } finally {
                triggerBtn.disabled = false;
            }
        };
    }

    const createBtn = document.getElementById('create-job-btn');
    if (createBtn) {
        createBtn.onclick = async () => {
            const nameEl = document.getElementById('new-job-name');
            const startEl = document.getElementById('new-job-start');
            const endEl = document.getElementById('new-job-end');
            const durEl = document.getElementById('new-job-duration');

            if (!nameEl.value || !startEl.value || !endEl.value) {
                return showToast('Please fill all fields', 'error');
            }
            
            try {
                const url = `/scheduled-jobs?job_name=${encodeURIComponent(nameEl.value)}&start_time=${encodeURIComponent(startEl.value)}&end_time=${encodeURIComponent(endEl.value)}&duration=${encodeURIComponent(durEl.value)}`;
                const response = await fetch(url, { method: 'POST' });
                if (response.ok) {
                    showToast('Scheduled job created and ACTIVE!', 'success');
                    nameEl.value = '';
                    startEl.value = '';
                    endEl.value = '';
                    durEl.value = '';
                    await fetchScheduledJobs();
                }
            } catch (e) {}
        };
    }

    const closeModal = document.getElementById('close-modal');
    if (closeModal) {
        closeModal.onclick = () => {
            document.getElementById('job-modal').classList.add('hidden');
        };
    }

    // Auto-calculate duration automatically with robust listeners and fallback
    const startInput = document.getElementById('new-job-start');
    const endInput = document.getElementById('new-job-end');
    const durInput = document.getElementById('new-job-duration');
    
    if (startInput && endInput && durInput) {
        const updateDur = () => {
            if (startInput.value && endInput.value) {
                const [h1, m1] = startInput.value.split(':').map(Number);
                const [h2, m2] = endInput.value.split(':').map(Number);
                let diffMin = (h2 * 60 + m2) - (h1 * 60 + m1);
                if (diffMin < 0) diffMin += 1440; // Over midnight
                
                const hours = Math.floor(diffMin / 60);
                const mins = diffMin % 60;
                durInput.value = `${hours > 0 ? hours + 'h ' : ''}${mins}m`;
            } else {
                durInput.value = '';
            }
        };
        startInput.addEventListener('input', updateDur);
        endInput.addEventListener('input', updateDur);
        setInterval(updateDur, 1000); // Fail-safe check
    }

    // Theme Toggle Logic (Robust Implementation)
    const themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        themeBtn.onclick = () => {
            const isLight = document.body.classList.toggle('light-theme');
            document.documentElement.classList.toggle('light-theme', isLight);
            
            themeBtn.innerText = isLight ? '🌙' : '☀️';
            try {
                localStorage.setItem('theme', isLight ? 'light' : 'dark');
            } catch (e) {}
            
            showToast(`${isLight ? 'Light' : 'Dark'} Mode Activated`, 'success');
            console.log(`Theme switched to: ${isLight ? 'Light' : 'Dark'}`);
            
            // Re-sync Chart Colors
            if (volumeChart && successChart) {
                const gridColor = isLight ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)';
                const textColor = isLight ? '#64748b' : '#94a3b8';
                
                volumeChart.options.scales.y.grid.color = gridColor;
                volumeChart.options.scales.y.ticks.color = textColor;
                volumeChart.options.scales.x.ticks.color = textColor;
                successChart.options.plugins.legend.labels.color = textColor;
                
                volumeChart.update();
                successChart.update();
            }
        };
    }
}

async function fetchData() {
    await fetchReports();
    await fetchJobLogs();
}

function initCharts() {
    if (typeof Chart === 'undefined') {
        console.error("Chart.js not loaded");
        return;
    }
    const isLight = document.body.classList.contains('light-theme');
    const gridColor = isLight ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)';
    const textColor = isLight ? '#475569' : '#94a3b8';

    const ctxV = document.getElementById('volumeChart');
    if (ctxV) {
        if (volumeChart) volumeChart.destroy();
        volumeChart = new Chart(ctxV, {
            type: 'bar',
            data: { 
                labels: [], 
                datasets: [{ 
                    label: 'Volume (₹)', 
                    data: [], 
                    backgroundColor: '#6366f1',
                    borderRadius: 8,
                    maxBarThickness: 50,
                    hoverBackgroundColor: '#4f46e5'
                }] 
            },
            options: { 
                responsive: true, 
                maintainAspectRatio: false, 
                plugins: { 
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return ` Volume: ₹${context.raw.toLocaleString('en-IN')}`;
                            }
                        }
                    }
                }, 
                scales: { 
                    y: { 
                        beginAtZero: true, 
                        grid: { color: gridColor }, 
                        ticks: { 
                            color: textColor, 
                            font: { weight: '700' },
                            callback: function(value) {
                                if (value >= 100000) return '₹' + (value/100000).toFixed(1) + 'L';
                                return '₹' + value.toLocaleString();
                            }
                        } 
                    }, 
                    x: { 
                        grid: { display: false }, 
                        ticks: { color: textColor, font: { weight: '700' } } 
                    } 
                } 
            },
            plugins: [{
                id: 'volumeText',
                beforeDraw: (chart) => {
                    const { ctx, chartArea: { top, right } } = chart;
                    ctx.save();
                    const total = chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                    ctx.font = 'bold 0.9rem Inter';
                    ctx.fillStyle = textColor;
                    ctx.textAlign = 'right';
                    ctx.fillText('TOTAL: ₹' + (total/100000).toFixed(2) + 'L', right, top - 10);
                    ctx.restore();
                }
            }]
        });
    }

    const ctxS = document.getElementById('successChart');
    if (ctxS) {
        if (successChart) successChart.destroy();
        successChart = new Chart(ctxS, {
            type: 'doughnut',
            data: { 
                labels: ['Success', 'Failed'], 
                datasets: [{ 
                    data: [0, 0], 
                    backgroundColor: ['#10b981', '#ef4444'], 
                    hoverOffset: 15,
                    borderWidth: 0,
                    borderRadius: 5
                }] 
            },
            options: { 
                responsive: true, 
                maintainAspectRatio: false, 
                cutout: '75%', 
                plugins: { 
                    legend: { 
                        position: 'bottom', 
                        labels: { color: textColor, padding: 30, font: { size: 14, weight: '700' } } 
                    },
                    tooltip: {
                        callbacks: {
                            label: function(item) {
                                let total = item.dataset.data.reduce((a, b) => a + b, 0);
                                let val = item.raw;
                                let perc = total > 0 ? Math.round((val / total) * 100) : 0;
                                return ` ${item.label}: ${val} (${perc}%)`;
                            }
                        }
                    }
                } 
            },
            plugins: [{
                id: 'centerText',
                afterDraw: (chart) => {
                    const { ctx, chartArea: { top, bottom, left, right, width, height } } = chart;
                    ctx.save();
                    const total = chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                    const success = chart.data.datasets[0].data[0];
                    const percentage = total > 0 ? Math.round((success / total) * 100) : 0;
                    
                    ctx.font = 'bold 2.5rem Outfit';
                    ctx.fillStyle = percentage > 80 ? '#10b981' : (percentage > 50 ? '#f59e0b' : '#ef4444');
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(percentage + '%', left + width / 2, top + height / 2 - 10);
                    
                    ctx.font = '600 0.85rem Inter';
                    ctx.fillStyle = textColor;
                    ctx.fillText('SUCCESS RATE', left + width / 2, top + height / 2 + 30);
                    ctx.restore();
                }
            }]
        });
    }
}

async function fetchReports() {
    try {
        const response = await fetch('/reports');
        const data = await response.json();
        renderReports(data.reports);
    } catch (e) {}
}


function renderReports(reports) {
    const tbody = document.getElementById('reports-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    
    let totalAmt = 0;
    let totalCtx = 0;

    if (!reports || reports.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; color: var(--text-dim);">No reports available. Trigger a job to start.</td></tr>';
        return;
    }

    reports.forEach(r => {
        totalAmt += r.total_amount || 0;
        totalCtx += r.transaction_count || 0;
        tbody.innerHTML += `
            <tr>
                <td>${formatDisplayDate(r.report_date)}</td>
                <td>
                    <span style="color: #10b981; font-weight:700">₹${(r.total_amount || 0).toLocaleString('en-IN')}</span><br>
                    <span class="amount-words" style="font-size: 0.75rem; color: var(--text-dim); display: block; margin-top: 2px;">${numberToWords(r.total_amount || 0)}</span>
                </td>
                <td>${r.transaction_count || 0}</td>
                <td>${new Date(r.processed_at).toLocaleDateString()} <br> <small>${formatTime12hr(r.processed_at)}</small></td>
                <td>
                    <div class="action-btns">
                        <button class="primary-btn" style="padding: 0.35rem 0.8rem; font-size: 0.75rem; background: var(--primary);" onclick="showReportDetails('${r.report_date}')">Details</button>
                        <button class="icon-btn" onclick="downloadReportPDF('${r.report_date}')" title="Download PDF">📥</button>
                        <button class="icon-btn delete-btn" onclick="deleteReport(${r.id})">🗑</button>
                    </div>
                </td>
            </tr>
        `;
    });
    
    document.getElementById('total-amount').innerText = `₹${totalAmt.toLocaleString('en-IN')}`;
    document.getElementById('total-count').innerText = totalCtx.toLocaleString();

    // Update Volume Chart
    if (volumeChart && reports.length > 0) {
        const sorted = [...reports].sort((a,b) => new Date(a.processed_at) - new Date(b.processed_at));
        // Take last 7 reports for clarity
        const recent = sorted.slice(-7);
        volumeChart.data.labels = recent.map(r => formatDisplayDate(r.report_date));
        volumeChart.data.datasets[0].data = recent.map(r => r.total_amount);
        volumeChart.update();
    }
}

async function showReportDetails(date) {
    try {
        const response = await fetch(`/job-logs/by-date/${date}`);
        if (response.ok) {
            const log = await response.json();
            openModalWithLog(log);
        } else {
            showToast('No execution log found for this report date.', 'error');
        }
    } catch (e) {
        showToast('Error fetching details', 'error');
    }
}

function openModalWithLog(log) {
    document.getElementById('modal-job-name').innerText = log.job_name || 'Manual Run';
    document.getElementById('det-start').innerText = formatDateTime12hr(log.start_time);
    document.getElementById('det-end').innerText = log.end_time ? formatDateTime12hr(log.end_time) : (log.status === 'Running' ? 'In Progress...' : '-');
    document.getElementById('det-dur').innerText = log.duration || (log.status === 'Running' ? 'Calculating...' : '-');
    document.getElementById('det-retry').innerText = log.retry_count || 0;
    document.getElementById('det-error').innerText = log.error_message || 'None';
    document.getElementById('det-logs').innerText = log.logs || 'Initializing logs...';
    document.getElementById('job-modal').classList.remove('hidden');
}

async function fetchJobLogs() {
    try {
        const response = await fetch('/job-logs');
        const logs = await response.json();
        currentLogs = logs || [];
        const tbody = document.getElementById('job-logs-body');
        if (!tbody) return;
        tbody.innerHTML = '';
        
        let completed = 0, failed = 0;

        if (currentLogs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-dim);">No execution logs found.</td></tr>';
            return;
        }

        currentLogs.forEach((l, index) => {
            const status = l.status || 'Unknown';
            if (status === 'Success') completed++;
            if (status === 'Failed') failed++;

            tbody.innerHTML += `
                <tr>
                    <td>#${l.id}</td>
                    <td>${l.job_name || 'Manual Run'}</td>
                    <td>${l.duration || (status === 'Running' ? '<span class="loader-small"></span>' : '-')}</td>
                    <td>${l.retry_count || 0}/3 ${l.status === 'Failed' ? `<button class="retry-badge-btn" onclick="retryJob(${l.id})">🔁 Retry</button>` : ''}</td>
                    <td><span class="status-tag status-${status.toLowerCase()}">${status}</span></td>
                    <td>
                        <div class="action-btns">
                            <button class="primary-btn" style="padding: 0.3rem 0.8rem; font-size: 0.75rem;" onclick="showJobDetails(${index})">Details</button>
                            <button class="icon-btn delete-btn" onclick="deleteJobLog(${l.id})">🗑</button>
                        </div>
                    </td>
                </tr>
            `;
        });
        document.getElementById('completed-count').innerText = completed;
        document.getElementById('failed-count').innerText = failed;

        // Update Success Distribution Chart
        if (successChart && (completed > 0 || failed > 0)) {
            successChart.data.datasets[0].data = [completed, failed];
            successChart.update();
        }
    } catch (e) {}
}

async function retryJob(id) {
    showToast('Retrying failed job...', 'success');
    await fetch(`/retry_job/${id}`, { method: 'POST' });
    await fetchData();
}

function showJobDetails(index) {
    const log = currentLogs[index];
    if (!log) return;
    openModalWithLog(log);
}

// Robust Indian Number System to Words
function numberToWords(num) {
    if (num === 0) return 'Zero Rupees';
    
    const ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'];
    const tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety'];
    
    function convert_less_than_thousand(n) {
        if (n === 0) return '';
        if (n < 20) return ones[n];
        if (n < 100) return tens[Math.floor(n / 10)] + (n % 10 !== 0 ? ' ' + ones[n % 10] : '');
        return ones[Math.floor(n / 100)] + ' Hundred' + (n % 100 !== 0 ? ' and ' + convert_less_than_thousand(n % 100) : '');
    }

    let n = Math.floor(num);
    let str = '';
    
    if (n >= 10000000) {
        str += convert_less_than_thousand(Math.floor(n / 10000000)) + ' Crore ';
        n %= 10000000;
    }
    if (n >= 100000) {
        str += convert_less_than_thousand(Math.floor(n / 100000)) + ' Lakh ';
        n %= 100000;
    }
    if (n >= 1000) {
        str += convert_less_than_thousand(Math.floor(n / 1000)) + ' Thousand ';
        n %= 1000;
    }
    str += convert_less_than_thousand(n);
    
    return str.trim() + ' Rupees';
}

function formatDisplayDate(dateStr) {
    if (!dateStr) return '-';
    // If it looks like YYYY-MM-DD, format it nicely
    try {
        const date = new Date(dateStr);
        if (!isNaN(date.getTime()) && dateStr.includes('-')) {
            return date.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' }).replace(/\//g, '-');
        }
    } catch (e) {}
    return dateStr; // Fallback
}

function formatTime12hr(dateString) {
    if (!dateString) return '-';
    try {
        const date = new Date(dateString);
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
    } catch (e) { return '-'; }
}

function formatDateTime12hr(dateString) {
    if (!dateString || dateString === 'N/A' || dateString === 'TBD') return dateString || '-';
    try {
        const date = new Date(dateString);
        if (isNaN(date.getTime())) return dateString;
        const datePart = date.toLocaleDateString();
        const timePart = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
        return `${datePart} ${timePart}`;
    } catch (e) { return dateString; }
}

function showToast(msg, type) {
    const area = document.getElementById('notification-area');
    if (!area) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerText = msg;
    area.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 500);
    }, 3500);
}

// Global functions for inline onclicks
window.deleteReport = async (id) => {
    if (!confirm("Are you sure?")) return;
    await fetch(`/reports/${id}`, { method: 'DELETE' });
    await fetchData();
    showToast('Report deleted', 'success');
};

async function fetchScheduledJobs() {
    const response = await fetch('/scheduled-jobs');
    const jobs = await response.json();
    const tbody = document.getElementById('scheduled-jobs-body');
    if (!tbody) return;
    tbody.innerHTML = '';
    
    jobs.forEach(j => {
        const status = j.status || 'Active';
        
        tbody.innerHTML += `
            <tr>
                <td>
                    <div style="display:flex; flex-direction:column;">
                        <span style="font-weight:700; font-size:1rem;">${j.job_name}</span>
                        <span style="font-size:0.75rem; color:var(--text-dim);">ID: #${j.id}</span>
                    </div>
                </td>
                <td><span class="status-tag status-${status.toLowerCase()}">${status}</span></td>
                <td>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span style="color:var(--primary); font-weight:600;">${j.schedule_time}</span>
                        <span style="color:var(--text-dim); font-size:0.8rem;">to</span>
                        <span style="color:var(--primary); font-weight:600;">${j.next_run.split(' - ')[1]?.split(' ')[0] || '-'}</span>
                    </div>
                </td>
                <td>
                    <div class="action-btns">
                        <button class="primary-btn" style="padding: 0.3rem 0.7rem; font-size: 0.75rem;" onclick="showScheduledDetails(${j.id})">Details</button>
                        <button class="icon-btn" onclick="toggleJob(${j.id})" title="Toggle Active/Pause">${status === 'Active' ? '⏸' : '▶'}</button>
                        <button class="icon-btn" onclick="editJob(${j.id})" title="Edit Job">✏️</button>
                        <button class="icon-btn delete-btn" onclick="deleteScheduledJob(${j.id})" title="Delete Job">🗑</button>
                    </div>
                </td>
            </tr>
        `;
    });
}

window.showScheduledDetails = (id) => {
    showToast(`Opening technical details for Job #${id}`, 'success');
};

window.editJob = (id) => {
    showToast(`Edit mode activated for Job #${id}`, 'success');
};

window.toggleJob = async (id) => {
    await fetch(`/scheduled-jobs/${id}/toggle`, { method: 'POST' });
    await fetchScheduledJobs();
};

window.deleteScheduledJob = async (id) => {
    if (!confirm("Delete this scheduled job?")) return;
    await fetch(`/scheduled-jobs/${id}`, { method: 'DELETE' });
    await fetchScheduledJobs();
    showToast('Scheduled job deleted', 'success');
};

window.deleteJobLog = async (id) => {
    if (!confirm("Delete this execution log?")) return;
    await fetch(`/job-logs/${id}`, { method: 'DELETE' });
    await fetchData();
    showToast('Execution log removed', 'success');
};

window.downloadReportPDF = (date) => {
    showToast('Preparing PDF Report...', 'success');
    window.location.href = `/download-report/${date}`;
};

window.downloadExecutionHistory = () => {
    showToast('Exporting Execution History...', 'success');
    window.location.href = `/download-history`;
};

window.downloadFullHistory = () => {
    showToast('Preparing Full System Export...', 'success');
    window.location.href = `/download-history`;
};
