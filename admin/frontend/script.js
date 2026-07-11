/*
 * Admin Dashboard JavaScript
 */

// Import configuration
// Since we can't directly import Python config in JavaScript, we'll define it here
// In a production environment, this would typically come from environment variables or a config endpoint

// Configuration constants
const CONFIG = {
    FRONTEND_HOST: "localhost",
    FRONTEND_PORT: 8001,
    BACKEND_HOST: "localhost",
    BACKEND_PORT: 5001
};

// API base URL using configuration
const API_BASE_URL = `http://${CONFIG.BACKEND_HOST}:${CONFIG.BACKEND_PORT}/api`;

// Function to truncate names for better X-axis readability
function truncateName(fullName) {
    if (!fullName || typeof fullName !== 'string') return 'Unknown';
    
    // Split name into parts
    const nameParts = fullName.trim().split(' ');
    
    if (nameParts.length === 1) {
        // If only one name, return as is (or first 15 chars)
        return nameParts[0].length > 15 ? nameParts[0].substring(0, 15) + '...' : nameParts[0];
    } else {
        // Return first name + last initial
        const firstName = nameParts[0];
        const lastNameInitial = nameParts[nameParts.length - 1][0];
        
        // Combine and truncate if needed
        const combined = `${firstName} ${lastNameInitial}.`;
        return combined.length > 15 ? combined.substring(0, 15) + '...' : combined;
    }
}

// DOM Elements for Employee Movement
const movementTableBody = document.querySelector('#movement-table tbody');
const refreshMovementBtn = document.getElementById('refresh-movement');

// DOM Elements for Daily IN/OUT Summary
const inoutSummaryTableBody = document.querySelector('#inout-summary-table tbody');
const refreshInOutSummaryBtn = document.getElementById('refresh-inout-summary');

// Global variables to store current data and state
let currentSummaryData = [];
let filteredSummaryData = [];
let currentDowntimeData = [];
let filteredDowntimeData = [];

let currentSort = { column: null, direction: 'asc' };
let currentRegisteredUsersData = [];

// KPI and chart data
let currentKpiData = {};
let currentChartData = {};

// Cache for aggregated data to optimize performance
let aggregatedDataCache = {};
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes in milliseconds

// DOM Elements
const totalCamerasEl = document.getElementById('total-cameras');
const activeCamerasEl = document.getElementById('active-cameras');
const totalEmployeesEl = document.getElementById('total-employees');
const totalRecognitionsEl = document.getElementById('total-recognitions');
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebar = document.getElementById('sidebar');

// Debugging: Log DOM elements to verify they exist
console.log('DOM Elements:', { totalCamerasEl, activeCamerasEl, totalEmployeesEl, totalRecognitionsEl });

const fromDateEl = document.getElementById('from-date');
const toDateEl = document.getElementById('to-date');
const applyFilterBtn = document.getElementById('apply-filter');

const refreshCamerasBtn = document.getElementById('refresh-cameras');
const refreshSummaryBtn = document.getElementById('refresh-summary');
const refreshDowntimeBtn = document.getElementById('refresh-downtime');

const camerasTableBody = document.querySelector('#cameras-table tbody');
const summaryTableBody = document.querySelector('#summary-table tbody');
const downtimeTableBody = document.querySelector('#downtime-table tbody');


// Search elements
const summarySearchEl = document.getElementById('summary-search');
const downtimeSearchEl = document.getElementById('downtime-search');
const downtimeFromDateEl = document.getElementById('downtime-from-date');
const downtimeToDateEl = document.getElementById('downtime-to-date');
const applyDowntimeFilterBtn = document.getElementById('apply-downtime-filter');


// View elements
const dashboardView = document.getElementById('dashboard-view');
const camerasView = document.getElementById('cameras-view');
const summaryView = document.getElementById('summary-view');
const downtimeView = document.getElementById('downtime-view');
const addCameraView = document.getElementById('add-camera-view');
const updateCameraStatusView = document.getElementById('update-camera-status-view');
const employeeMovementView = document.getElementById('employee-movement-view');
const registeredUsersView = document.getElementById('registered-users-view');
const registeredUsersTableBody = document.querySelector('#registered-users-table tbody');
const refreshRegisteredUsersBtn = document.getElementById('refresh-registered-users');
const registeredUsersSearchEl = document.getElementById('registered-users-search');

// Daily IN/OUT Summary view element
const dailyInOutSummaryView = document.getElementById('daily-inout-summary-view');

// Location Coverage Report view element
const locationCoverageView = document.getElementById('location-coverage-view');

// Sidebar navigation links
const dashboardLink = document.getElementById('dashboard-link');
const reportsDropdown = document.getElementById('reports-dropdown');
const camerasLink = document.getElementById('cameras-link');
const summaryLink = document.getElementById('summary-link');
const downtimeLink = document.getElementById('downtime-link');
const faceRecognitionLink = document.getElementById('face-recognition-link');
const addCameraLink = document.getElementById('add-camera-link');
const updateCameraStatusLink = document.getElementById('update-camera-status-link');
const cameraInfoDropdown = document.getElementById('camera-info-dropdown');

// Report links (newly added)
const reportLinks = document.querySelectorAll('.report-link');
const cameraInfoLinks = document.querySelectorAll('.camera-info-link');
const drishtiManagementDropdown = document.getElementById('drishti-management-dropdown');

// Set default dates (last 7 days)
function setDefaultDates() {
    const today = new Date();
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);
    
    // Format as YYYY-MM-DD
    const todayStr = today.toISOString().split('T')[0];
    const lastWeekStr = lastWeek.toISOString().split('T')[0];
    
    // Only set values if elements exist
    if (toDateEl) {
        toDateEl.value = todayStr;
    }
    if (fromDateEl) {
        fromDateEl.value = lastWeekStr;
    }
    
    // Set default dates for downtime view as well
    if (downtimeToDateEl) {
        downtimeToDateEl.value = todayStr;
    }
    if (downtimeFromDateEl) {
        downtimeFromDateEl.value = lastWeekStr;
    }
}

// Show alert message
function showAlert(message, type = 'info') {
    // Remove existing alerts
    const existingAlert = document.querySelector('.alert-fixed');
    if (existingAlert) {
        existingAlert.remove();
    }
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-fixed`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.parentNode.removeChild(alertDiv);
        }
    }, 3000);
}

// Render movement data in the table
function renderMovementData(movementData) {
    if (!movementData || movementData.length === 0) {
        movementTableBody.innerHTML = '<tr><td colspan="12" class="text-center">No movement data found</td></tr>';
        return;
    }
    
    let html = '';
    movementData.forEach(record => {
        html += `
            <tr>
                <td>${record.REC_DATE ? new Date(record.REC_DATE).toLocaleDateString() : '-'}</td>
                <td>${record.EMPLOYEE_ID || '-'}</td>
                <td>${record.NAME || '-'}</td>
                <td>${record.DEPARTMENT || '-'}</td>
                <td>${record.BUILDING_NAME || '-'}</td>
                <td>${record.FLOOR_NAME || '-'}</td>
                <td>${record.LOCATION_STATUS || '-'}</td>
                <td>${record.FIRST_SEEN_TIME || '-'}</td>
                <td>${record.LAST_SEEN_TIME || '-'}</td>
                <td>${record.ROW_TOTAL_MINUTES || 0}</td>
                <td>${record.TOTAL_HITS || 0}</td>
            </tr>
        `;
    });
    
    movementTableBody.innerHTML = html;
}

// Render Daily IN/OUT Summary data in the table
function renderInOutSummaryData(inoutData) {
    if (!inoutData || inoutData.length === 0) {
        inoutSummaryTableBody.innerHTML = '<tr><td colspan="6" class="text-center">No IN/OUT summary data found</td></tr>';
        return;
    }
    
    let html = '';
    inoutData.forEach(record => {
        html += `
            <tr>
                <td>${record.REC_DATE ? new Date(record.REC_DATE).toLocaleDateString() : '-'}</td>
                <td>${record.EMPLOYEE_ID || '-'}</td>
                <td>${record.NAME || '-'}</td>
                <td>${record.TOTAL_INSIDE_MINUTES || 0}</td>
                <td>${record.TOTAL_OUTSIDE_MINUTES || 0}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary" onclick="openMovementDetails('${record.EMPLOYEE_ID}', '${record.REC_DATE ? String(record.REC_DATE).substring(0, 10) : ''}')">
                        <i class="fas fa-info-circle"></i> More Information
                    </button>
                </td>
            </tr>
        `;
    });
    
    inoutSummaryTableBody.innerHTML = html;
}

// Open movement details page with employee ID and date
function openMovementDetails(employeeId, recDate) {
    if (!employeeId || !recDate) {
        showAlert('Missing required parameters: employeeId and recDate', 'danger');
        return;
    }
    
    // Encode parameters to handle special characters
    const encodedEmployeeId = encodeURIComponent(employeeId);
    const encodedRecDate = encodeURIComponent(recDate);
    
    // Open the detailed view in the same tab/window
    const url = `employee-inout-details.html?employee_id=${encodedEmployeeId}&rec_date=${encodedRecDate}`;
    window.location.href = url;
}

// Open location coverage details page with employee ID and date
function openLocationCoverageDetails(employeeId, recDate) {
    if (!employeeId || !recDate) {
        showAlert('Missing required parameters: employeeId and recDate', 'danger');
        return;
    }
    
    // Encode parameters to handle special characters
    const encodedEmployeeId = encodeURIComponent(employeeId);
    const encodedRecDate = encodeURIComponent(recDate);
    
    // Open the detailed view in the same tab/window
    const url = `location-coverage-details.html?employee_id=${encodedEmployeeId}&date=${encodedRecDate}`;
    window.location.href = url;
}

// Also add the function to the global window object so it's available in HTML onclick attributes
window.openLocationCoverageDetails = openLocationCoverageDetails;

// Check if user is authenticated
function checkAuth() {
    const isLoggedIn = localStorage.getItem('isAdminLoggedIn');
    if (!isLoggedIn) {
        window.location.href = 'login.html';
        return false;
    }
    return true;
}

// Check if user has admin access
function hasAdminAccessSync() {
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
    
    // Check if admin access info is stored in the current user data
    if (currentUser.adminAccess !== undefined) {
        return currentUser.adminAccess === 'Y';
    }
    
    // Alternative: check if it's stored separately
    const adminAccess = localStorage.getItem('userAdminAccess');
    if (adminAccess) {
        return adminAccess === 'Y';
    }
    
    // If no cached information is available, return null to indicate we need to fetch
    return null;
}

// Check if user has admin access asynchronously
async function hasAdminAccess() {
    // First, check if we have the information cached
    const cachedResult = hasAdminAccessSync();
    if (cachedResult !== null) {
        return cachedResult;
    }
    
    // If not cached, fetch from backend
    const currentUser = JSON.parse(localStorage.getItem('currentUser') || '{}');
    
    try {
        const response = await fetch(`${API_BASE_URL}/admin-access-users`);
        const result = await response.json();
        
        if (result.success && result.data) {
            // Check if current user is in the admin access list
            const currentUserEmployeeId = currentUser.employee_id;
            const isAdmin = result.data.some(user => 
                user.EMPLOYEE_ID === currentUserEmployeeId && user.ADMIN_ACCESS === 'Y'
            );
            
            // Store the result in localStorage for future use
            localStorage.setItem('userAdminAccess', isAdmin ? 'Y' : 'N');
            
            // Also update the currentUser object with admin access info
            if (currentUser) {
                currentUser.adminAccess = isAdmin ? 'Y' : 'N';
                localStorage.setItem('currentUser', JSON.stringify(currentUser));
            }
            
            return isAdmin;
        }
    } catch (error) {
        console.error('Error fetching admin access status:', error);
    }
    
    return false;
}

// Update the sidebar to show/hide Drishti Management based on admin access
async function updateSidebarForAdminAccess() {
    const drishtiManagementSection = document.querySelector('[data-bs-target="#drishti-management-submenu"]');
    const drishtiManagementSubmenu = document.getElementById('drishti-management-submenu');
    
    if (!drishtiManagementSection || !drishtiManagementSubmenu) {
        console.warn('Drishti Management elements not found');
        return;
    }
    
    // First, check if we have cached admin access information
    const cachedResult = hasAdminAccessSync();
    
    if (cachedResult !== null) {
        // We have cached information, update UI immediately
        if (cachedResult) {
            // Show the Drishti Management section
            drishtiManagementSection.style.display = '';
            drishtiManagementSection.classList.remove('d-none', 'hidden-initially');
            // Make sure the parent li element is also visible
            const parentLi = drishtiManagementSection.closest('li');
            if (parentLi) {
                parentLi.style.display = '';
                parentLi.classList.remove('d-none', 'hidden-initially');
            }
            // Show the submenu if needed
            drishtiManagementSubmenu.classList.remove('d-none', 'hidden-initially');
        } else {
            // Hide the Drishti Management section
            drishtiManagementSection.style.display = 'none';
            drishtiManagementSection.classList.add('d-none');
            const parentLi = drishtiManagementSection.closest('li');
            if (parentLi) {
                parentLi.style.display = 'none';
                parentLi.classList.add('d-none');
            }
            // Also hide the submenu
            drishtiManagementSubmenu.classList.add('d-none');
            drishtiManagementSubmenu.classList.remove('show');
            drishtiManagementSection.setAttribute('aria-expanded', 'false');
        }
    }
    
    // Now, fetch the latest admin access status in the background to update cache
    const isAdmin = await hasAdminAccess();
    
    // If the fetched result is different from the cached result, update the UI again
    if (cachedResult !== null && cachedResult !== isAdmin) {
        if (isAdmin) {
            // Show the Drishti Management section
            drishtiManagementSection.style.display = '';
            drishtiManagementSection.classList.remove('d-none', 'hidden-initially');
            // Make sure the parent li element is also visible
            const parentLi = drishtiManagementSection.closest('li');
            if (parentLi) {
                parentLi.style.display = '';
                parentLi.classList.remove('d-none', 'hidden-initially');
            }
            // Show the submenu if needed
            drishtiManagementSubmenu.classList.remove('d-none', 'hidden-initially');
        } else {
            // Hide the Drishti Management section
            drishtiManagementSection.style.display = 'none';
            drishtiManagementSection.classList.add('d-none');
            const parentLi = drishtiManagementSection.closest('li');
            if (parentLi) {
                parentLi.style.display = 'none';
                parentLi.classList.add('d-none');
            }
            // Also hide the submenu
            drishtiManagementSubmenu.classList.add('d-none');
            drishtiManagementSubmenu.classList.remove('show');
            drishtiManagementSection.setAttribute('aria-expanded', 'false');
        }
    }
}

// Fetch dashboard stats
async function fetchDashboardStats() {
    if (!checkAuth()) return Promise.resolve();
    
    try {
        console.log('Fetching dashboard stats...');
        const response = await fetch(`${API_BASE_URL}/dashboard-stats`);
        const result = await response.json();
        console.log('Dashboard stats response:', result);
        
        if (result.success) {
            const stats = result.data;
            console.log('Dashboard stats data:', stats);
            
            // Ensure DOM elements exist before updating
            if (totalCamerasEl) {
                totalCamerasEl.textContent = stats.total_cameras || 0;
                console.log('Updated totalCamerasEl:', stats.total_cameras);
            }
            if (activeCamerasEl) {
                activeCamerasEl.textContent = stats.active_cameras || 0;
                console.log('Updated activeCamerasEl:', stats.active_cameras);
            }
            if (totalEmployeesEl) {
                totalEmployeesEl.textContent = stats.total_employees || 0;
                console.log('Updated totalEmployeesEl:', stats.total_employees);
            }
            if (totalRecognitionsEl) {
                totalRecognitionsEl.textContent = stats.total_recognitions || 0;
                console.log('Updated totalRecognitionsEl:', stats.total_recognitions);
            }
        } else {
            showAlert('Failed to load dashboard stats: ' + (result.error || 'Unknown error'), 'danger');
        }
        return Promise.resolve();
    } catch (error) {
        console.error('Error in fetchDashboardStats:', error); // Log the full error for debugging
        showAlert('Error loading dashboard stats: ' + (error.message || 'Network error'), 'danger');
        return Promise.reject(error);
    }
}

// Fetch camera registry data
async function fetchCameras() {
    if (!checkAuth()) return Promise.resolve();
    
    try {
        // Clear table
        camerasTableBody.innerHTML = '<tr><td colspan="10" class="text-center">Loading...</td></tr>';
        
        const response = await fetch(`${API_BASE_URL}/cameras`);
        const result = await response.json();
        
        if (result.success) {
            renderCameras(result.data);
        } else {
            camerasTableBody.innerHTML = `<tr><td colspan="10" class="text-center text-danger">Error: ${result.error}</td></tr>`;
            showAlert('Failed to load cameras: ' + result.error, 'danger');
        }
        return Promise.resolve();
    } catch (error) {
        camerasTableBody.innerHTML = `<tr><td colspan="10" class="text-center text-danger">Error: ${error.message}</td></tr>`;
        showAlert('Error loading cameras: ' + error.message, 'danger');
        return Promise.reject(error);
    }
}

// Render camera registry data
function renderCameras(cameras) {
    if (cameras.length === 0) {
        camerasTableBody.innerHTML = '<tr><td colspan="10" class="text-center">No cameras found</td></tr>';
        return;
    }
    
    let html = '';
    cameras.forEach(camera => {
        const statusClass = camera.IS_ACTIVE === 'Y' ? 'status-active' : 'status-inactive';
        const statusText = camera.IS_ACTIVE === 'Y' ? 'Active' : 'Inactive';
        
        html += `
            <tr>
                <td>${camera.CAMERA_ID}</td>
                <td>${camera.CAMERA_NAME}</td>
                <td>${camera.LOCATION_TYPE}</td>
                <td>${camera.SITE_NAME || '-'}</td>
                <td>${camera.BUILDING_NAME || '-'}</td>
                <td>${camera.FLOOR_NAME || camera.FLOOR_NO || '-'}</td>
                <td>${camera.AREA_NAME || '-'}</td>
                <td>${camera.DIRECTION || '-'}</td>
                <td>${camera.IP_ADDRESS || '-'}</td>
                <td class="${statusClass}">${statusText}</td>
            </tr>
        `;
    });
    
    camerasTableBody.innerHTML = html;
}

// Fetch employee summary data
async function fetchEmployeeSummary(fromDate, toDate) {
    if (!checkAuth()) return Promise.resolve();
    
    try {
        // Clear table
        summaryTableBody.innerHTML = '<tr><td colspan="9" class="text-center">Loading...</td></tr>';
        
        const url = `${API_BASE_URL}/employee-summary?from_date=${fromDate}&to_date=${toDate}`;
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.success) {
            // Store the raw data
            currentSummaryData = result.data;
            filteredSummaryData = [...currentSummaryData];
            
            // Store KPI and chart data if available
            if (result.kpi_data) {
                currentKpiData = result.kpi_data;
                
                // Cache the aggregated data
                const cacheKey = `${fromDate}-${toDate}`;
                aggregatedDataCache[cacheKey] = {
                    data: {
                        kpi_data: result.kpi_data,
                        chart_data: result.chart_data
                    },
                    timestamp: Date.now()
                };
            }
            
            if (result.chart_data) {
                currentChartData = result.chart_data;
            }
            
            // Apply any existing search filter
            applySearchFilter();
            
            // Render the data
            renderEmployeeSummary(filteredSummaryData);
            
            // Render KPI cards only if we're on the summary view
            if (isSummaryViewActive()) {
                renderKpiCards();
            }
        } else {
            summaryTableBody.innerHTML = `<tr><td colspan="9" class="text-center text-danger">Error: ${result.error}</td></tr>`;
            showAlert('Failed to load employee summary: ' + result.error, 'danger');
        }
        return Promise.resolve();
    } catch (error) {
        summaryTableBody.innerHTML = `<tr><td colspan="9" class="text-center text-danger">Error: ${error.message}</td></tr>`;
        showAlert('Error loading employee summary: ' + error.message, 'danger');
        return Promise.reject(error);
    }
}

// Fetch employee summary aggregated data
async function fetchEmployeeSummaryAggregated(fromDate, toDate) {
    if (!checkAuth()) return Promise.resolve();
    
    // Create cache key
    const cacheKey = `${fromDate}-${toDate}`;
    const now = Date.now();
    
    // Check if we have valid cached data
    if (aggregatedDataCache[cacheKey] && (now - aggregatedDataCache[cacheKey].timestamp) < CACHE_DURATION) {
        console.log('Using cached aggregated data');
        currentKpiData = aggregatedDataCache[cacheKey].data.kpi_data;
        currentChartData = aggregatedDataCache[cacheKey].data.chart_data;
        
        // Only render if we're on the summary view
        if (isSummaryViewActive()) {
            renderKpiCards();
        }
        return Promise.resolve();
    }
    
    try {
        // Show loading state only if we're on the summary view
        if (isSummaryViewActive()) {
            renderKpiCards(); // This will show loading indicators
        }
        
        const url = `${API_BASE_URL}/employee-summary-aggregated?from_date=${fromDate}&to_date=${toDate}`;
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            // Validate that required data exists
            if (!result.kpi_data || !result.chart_data) {
                console.error('Invalid response format: missing kpi_data or chart_data');
                showAlert('Invalid response format from server', 'danger');
                return Promise.resolve();
            }
            
            // Store KPI and chart data
            currentKpiData = result.kpi_data;
            currentChartData = result.chart_data;
            
            // Cache the data
            aggregatedDataCache[cacheKey] = {
                data: result,
                timestamp: now
            };
            
            // Render KPI cards if we're on the summary view
            if (isSummaryViewActive()) {
                renderKpiCards();
            }
        } else {
            console.error('Failed to load aggregated employee summary:', result.error);
            showAlert('Failed to load aggregated data: ' + (result.error || 'Unknown error'), 'danger');
            
            // Show error state in UI if we're on the summary view
            currentKpiData = {};
            currentChartData = {};
            if (isSummaryViewActive()) {
                renderKpiCards();
            }
        }
        return Promise.resolve();
    } catch (error) {
        console.error('Error loading aggregated employee summary:', error);
        showAlert('Error loading aggregated data: ' + error.message, 'danger');
        
        // Show error state in UI if we're on the summary view
        currentKpiData = {};
        currentChartData = {};
        if (isSummaryViewActive()) {
            renderKpiCards();
        }
        
        return Promise.reject(error);
    }
}

// Fetch new dashboard KPIs
async function fetchNewDashboardKpis(fromDate, toDate) {
    if (!checkAuth()) return Promise.resolve();
    
    try {
        // Show loading state
        const kpiContainer = document.querySelector('#kpi-cards-container');
        if (kpiContainer) {
            kpiContainer.innerHTML = `
                <div class="row mb-4">
                    <div class="col-md-2-4 mb-3">
                        <div class="card text-white" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
                            <div class="card-body text-center">
                                <div class="spinner-border text-light" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mt-2 mb-0">Loading...</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-2-4 mb-3">
                        <div class="card text-white" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
                            <div class="card-body text-center">
                                <div class="spinner-border text-light" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mt-2 mb-0">Loading...</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-2-4 mb-3">
                        <div class="card text-white" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
                            <div class="card-body text-center">
                                <div class="spinner-border text-light" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mt-2 mb-0">Loading...</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-2-4 mb-3">
                        <div class="card text-white" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
                            <div class="card-body text-center">
                                <div class="spinner-border text-light" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mt-2 mb-0">Loading...</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-2-4 mb-3">
                        <div class="card text-white" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
                            <div class="card-body text-center">
                                <div class="spinner-border text-light" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <p class="mt-2 mb-0">Loading...</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        const url = `${API_BASE_URL}/new-dashboard-kpis?from_date=${fromDate}&to_date=${toDate}`;
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.success) {
            // Store the new KPI data
            currentKpiData = result.kpis;
            
            // Render KPI cards
            renderKpiCards();
        } else {
            console.error('Failed to load new dashboard KPIs:', result.error);
            showAlert('Failed to load KPI data: ' + (result.error || 'Unknown error'), 'danger');
            
            // Show error state in UI
            currentKpiData = {};
            renderKpiCards();
        }
        return Promise.resolve();
    } catch (error) {
        console.error('Error loading new dashboard KPIs:', error);
        showAlert('Error loading KPI data: ' + error.message, 'danger');
        
        // Show error state in UI
        currentKpiData = {};
        renderKpiCards();
        
        return Promise.reject(error);
    }
}

// Helper function to check if summary view is active
function isSummaryViewActive() {
    const summaryView = document.getElementById('summary-view');
    return summaryView && !summaryView.classList.contains('d-none');
}

// Fetch employee downtime summary data
async function fetchDowntimeSummary(fromDate, toDate) {
    if (!checkAuth()) return Promise.resolve();
    
    try {
        // Clear table
        downtimeTableBody.innerHTML = '<tr><td colspan="7" class="text-center">Loading...</td></tr>';
        
        const url = `${API_BASE_URL}/downtime-summary?from_date=${fromDate}&to_date=${toDate}`;
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.success) {
            // Store the raw data
            currentDowntimeData = result.data;
            filteredDowntimeData = [...currentDowntimeData];
            
            // Apply any existing search filter
            applyDowntimeSearchFilter();
            
            // Render the data
            renderDowntimeSummary(filteredDowntimeData);
        } else {
            downtimeTableBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Error: ${result.error}</td></tr>`;
            showAlert('Failed to load downtime summary: ' + result.error, 'danger');
        }
        return Promise.resolve();
    } catch (error) {
        downtimeTableBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Error: ${error.message}</td></tr>`;
        showAlert('Error loading downtime summary: ' + error.message, 'danger');
        return Promise.reject(error);
    }
}



// Apply search filter to the employee summary data
function applySearchFilter() {
    const searchTerm = summarySearchEl.value.toLowerCase().trim();
    
    if (!searchTerm) {
        filteredSummaryData = [...currentSummaryData];
    } else {
        filteredSummaryData = currentSummaryData.filter(record => {
            return (
                (record.EMPLOYEE_ID && record.EMPLOYEE_ID.toString().includes(searchTerm)) ||
                (record.NAME && record.NAME.toLowerCase().includes(searchTerm)) ||
                (record.DEPARTMENT && record.DEPARTMENT.toLowerCase().includes(searchTerm))
            );
        });
    }
    
    // Apply sorting if active
    if (currentSort.column) {
        sortData(currentSort.column, currentSort.direction);
    }
}

// Apply search filter to the downtime summary data
function applyDowntimeSearchFilter() {
    const searchTerm = downtimeSearchEl.value.toLowerCase().trim();
    
    if (!searchTerm) {
        filteredDowntimeData = [...currentDowntimeData];
    } else {
        filteredDowntimeData = currentDowntimeData.filter(record => {
            return (
                (record.EMPLOYEE_ID && record.EMPLOYEE_ID.toString().includes(searchTerm)) ||
                (record.NAME && record.NAME.toLowerCase().includes(searchTerm)) ||
                (record.DEPARTMENT && record.DEPARTMENT.toLowerCase().includes(searchTerm))
            );
        });
    }
    
    // Apply sorting if active
    if (currentSort.column) {
        sortDowntimeData(currentSort.column, currentSort.direction);
    }
}

// Apply search filter to registered users data
function applyRegisteredUsersSearchFilter() {
    const searchTerm = registeredUsersSearchEl.value.toLowerCase().trim();
    
    if (!searchTerm) {
        // If no search term, show all users
        renderRegisteredUsers(currentRegisteredUsersData || []);
    } else {
        // Filter the current data based on search term
        const filteredUsers = currentRegisteredUsersData.filter(user => {
            return (
                (user.ID && user.ID.toString().includes(searchTerm)) ||
                (user.EMPLOYEE_ID && user.EMPLOYEE_ID.toString().includes(searchTerm)) ||
                (user.NAME && user.NAME.toLowerCase().includes(searchTerm)) ||
                (user.DEPARTMENT && user.DEPARTMENT.toLowerCase().includes(searchTerm))
            );
        });
        
        renderRegisteredUsers(filteredUsers);
    }
}



// Sort data by column for employee summary
function sortData(column, direction) {
    filteredSummaryData.sort((a, b) => {
        let aValue = a[column];
        let bValue = b[column];
        
        // Handle date sorting
        if (column === 'REC_DATE') {
            aValue = new Date(aValue);
            bValue = new Date(bValue);
        }
        
        // Handle numeric sorting
        if (column === 'EMPLOYEE_ID' || column === 'TOTAL_HITS' || column === 'TOTAL_FLOOR') {
            aValue = parseFloat(aValue) || 0;
            bValue = parseFloat(bValue) || 0;
        }
        
        // Handle time sorting (TOTAL_SPAN_HHMM)
        if (column === 'TOTAL_SPAN_HHMM') {
            // Convert HH:MM to minutes for comparison
            const parseTime = (timeStr) => {
                if (!timeStr) return 0;
                const parts = timeStr.split(':');
                return parseInt(parts[0]) * 60 + parseInt(parts[1]);
            };
            aValue = parseTime(aValue);
            bValue = parseTime(bValue);
        }
        
        // Handle string sorting
        if (typeof aValue === 'string') {
            aValue = aValue.toLowerCase();
            bValue = bValue.toLowerCase();
        }
        
        if (direction === 'asc') {
            return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
        } else {
            return aValue < bValue ? 1 : aValue > bValue ? -1 : 0;
        }
    });
}

// Sort data by column for downtime summary
function sortDowntimeData(column, direction) {
    filteredDowntimeData.sort((a, b) => {
        let aValue = a[column];
        let bValue = b[column];
        
        // Handle date sorting
        if (column === 'REC_DATE') {
            aValue = new Date(aValue);
            bValue = new Date(bValue);
        }
        
        // Handle numeric sorting
        if (column === 'EMPLOYEE_ID' || column === 'DOWNTIME_MINUTES' || column === 'DOWNTIME_EVENTS') {
            aValue = parseFloat(aValue) || 0;
            bValue = parseFloat(bValue) || 0;
        }
        
        // Handle string sorting
        if (typeof aValue === 'string') {
            aValue = aValue.toLowerCase();
            bValue = bValue.toLowerCase();
        }
        
        if (direction === 'asc') {
            return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
        } else {
            return aValue < bValue ? 1 : aValue > bValue ? -1 : 0;
        }
    });
}


// Render employee summary data
function renderEmployeeSummary(summaryData) {
    if (summaryData.length === 0) {
        summaryTableBody.innerHTML = '<tr><td colspan="9" class="text-center">No employee data found</td></tr>';
        return;
    }
    
    let html = '';
    summaryData.forEach(record => {
        html += `
            <tr>
                <td>${record.REC_DATE ? new Date(record.REC_DATE).toLocaleDateString() : '-'}</td>
                <td>${record.EMPLOYEE_ID}</td>
                <td>${record.NAME}</td>
                <td>${record.DEPARTMENT}</td>
                <td>${record.FIRST_SEEN_TIME || '-'}</td>
                <td>${record.LAST_SEEN_TIME || '-'}</td>
                <td>${record.TOTAL_SPAN_HHMM || record.TOTAL_SPAN_HOURS + ' hrs'}</td>
                <td>${record.TOTAL_HITS}</td>
                <td>${record.TOTAL_FLOOR}</td>
            </tr>
        `;
    });
    
    summaryTableBody.innerHTML = html;
}

// Render downtime summary data
function renderDowntimeSummary(downtimeData) {
    if (downtimeData.length === 0) {
        downtimeTableBody.innerHTML = '<tr><td colspan="7" class="text-center">No downtime data found</td></tr>';
        return;
    }
    
    let html = '';
    downtimeData.forEach(record => {
        html += `
            <tr>
                <td>${record.REC_DATE ? new Date(record.REC_DATE).toLocaleDateString() : '-'}</td>
                <td>${record.EMPLOYEE_ID}</td>
                <td>${record.NAME}</td>
                <td>${record.DEPARTMENT}</td>
                <td>${record.DOWNTIME_MINUTES}</td>
                <td>${record.DOWNTIME_EVENTS || '-'}</td>
            </tr>
        `;
    });
    
    downtimeTableBody.innerHTML = html;
}



// Fetch registered users data
async function fetchRegisteredUsers() {
    if (!checkAuth()) return Promise.resolve();
    
    try {
        // Clear table
        registeredUsersTableBody.innerHTML = '<tr><td colspan="6" class="text-center">Loading...</td></tr>';
        
        const response = await fetch(`${API_BASE_URL}/registered-users`);
        const result = await response.json();
        
        if (result.success) {
            currentRegisteredUsersData = result.data;
            renderRegisteredUsers(result.data);
        } else {
            registeredUsersTableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Error: ${result.error}</td></tr>`;
            showAlert('Failed to load registered users: ' + result.error, 'danger');
        }
        return Promise.resolve();
    } catch (error) {
        registeredUsersTableBody.innerHTML = `<tr><td colspan="6" class="text-center text-danger">Error: ${error.message}</td></tr>`;
        showAlert('Error loading registered users: ' + error.message, 'danger');
        return Promise.reject(error);
    }
}

// Fetch Daily IN/OUT Summary data
async function fetchInOutSummary(employeeId, fromDate, toDate) {
    if (!checkAuth()) return Promise.resolve();
    
    try {
        // Clear table
        inoutSummaryTableBody.innerHTML = '<tr><td colspan="5" class="text-center">Loading...</td></tr>';
        
        // Build the URL with parameters
        let url = `${API_BASE_URL}/daily-inout-summary?from_date=${fromDate}`;
        if (employeeId) {
            url += `&employee_id=${employeeId}`;
        }
        if (toDate) {
            url += `&to_date=${toDate}`;
        }
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.success) {
            renderInOutSummaryData(result.data);
        } else {
            inoutSummaryTableBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">Error: ${result.error}</td></tr>`;
            showAlert('Failed to load IN/OUT summary: ' + result.error, 'danger');
        }
        return Promise.resolve();
    } catch (error) {
        inoutSummaryTableBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">Error: ${error.message}</td></tr>`;
        showAlert('Error loading IN/OUT summary: ' + error.message, 'danger');
        return Promise.reject(error);
    }
}

// Render registered users data
function renderRegisteredUsers(users) {
    if (users.length === 0) {
        registeredUsersTableBody.innerHTML = '<tr><td colspan="6" class="text-center">No registered users found</td></tr>';
        return;
    }
    
    let html = '';
    users.forEach(user => {
        html += `
            <tr>
                <td>${user.ID || '-'}</td>
                <td>${user.EMPLOYEE_ID || '-'}</td>
                <td>${user.NAME || '-'}</td>
                <td>${user.DEPARTMENT || '-'}</td>
                <td>${user.CREATED_TIME || '-'}</td>
                <td>${user.CREATED_DATE ? new Date(user.CREATED_DATE).toLocaleDateString() : '-'}</td>
            </tr>
        `;
    });
    
    registeredUsersTableBody.innerHTML = html;
}

// Render KPI cards
function renderKpiCards() {
    // Check if KPI cards container exists in the DOM
    const kpiContainer = document.querySelector('#kpi-cards-container');
    if (!kpiContainer) {
        return; // Don't render if container doesn't exist
    }
    
    // Show loading state if no data is available yet
    if (!currentKpiData || Object.keys(currentKpiData).length === 0) {
        kpiContainer.innerHTML = `
            <div class="row mb-4">
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
                        <div class="card-body text-center">
                            <div class="spinner-border text-light" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2 mb-0">Loading...</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
                        <div class="card-body text-center">
                            <div class="spinner-border text-light" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2 mb-0">Loading...</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
                        <div class="card-body text-center">
                            <div class="spinner-border text-light" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2 mb-0">Loading...</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="row mb-4">
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
                        <div class="card-body text-center">
                            <div class="spinner-border text-light" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2 mb-0">Loading...</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
                        <div class="card-body text-center">
                            <div class="spinner-border text-light" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2 mb-0">Loading...</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
                        <div class="card-body text-center">
                            <div class="spinner-border text-light" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2 mb-0">Loading...</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
        return;
    }
    
    // Check if this is the new KPI data format (from new-dashboard-kpis endpoint)
    if (currentKpiData.employees_with_outside_time) {
        // This is the new KPI format
        const kpiCardsHtml = `
            <div class="row mb-4">
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #0d6efd 0%, #0b5ed7 100%);">
                        <div class="card-body">
                            <h5 class="card-title"><i class="fas fa-users"></i> Employees with Outside Time</h5>
                            <h2 class="mb-0">${currentKpiData.employees_with_outside_time.count_with_outside || 0} / ${currentKpiData.employees_with_outside_time.total_employees || 0}</h2>
                            <small>${currentKpiData.employees_with_outside_time.percentage || 0}% employees went OUT today</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #198754 0%, #157347 100%);">
                        <div class="card-body">
                            <h5 class="card-title"><i class="fas fa-clock"></i> Avg Outside Time</h5>
                            <h2 class="mb-0">${currentKpiData.avg_outside_time.minutes || 0} min</h2>
                            <small>
                                ${currentKpiData.avg_outside_time.comparison_to_yesterday > 0 ? '<i class="fas fa-arrow-up text-danger"></i> +' : '<i class="fas fa-arrow-down text-success"></i> '}${Math.abs(currentKpiData.avg_outside_time.comparison_to_yesterday)} min vs yesterday
                            </small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #0dcaf0 0%, #3dd5f3 100%);">
                        <div class="card-body">
                            <h5 class="card-title"><i class="fas fa-user-clock"></i> Highest Outside Time</h5>
                            <h2 class="mb-0">${currentKpiData.highest_outside_time.hours_formatted || '0h 0m'}</h2>
                            <small>Employee: ${currentKpiData.highest_outside_time.employee_id || 'N/A'}</small>
                        </div>
                    </div>
                </div>
            </div>
            <div class="row mb-4">
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #fd7e14 0%, #fd9248 100%);">
                        <div class="card-body">
                            <h5 class="card-title"><i class="fas fa-exchange-alt"></i> Inside vs Outside</h5>
                            <h2 class="mb-0">${currentKpiData.inside_vs_outside_ratio.inside_percentage || 0}% / ${currentKpiData.inside_vs_outside_ratio.outside_percentage || 0}%</h2>
                            <small>Organization-level time split</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #6f42c1 0%, #7d5da8 100%);">
                        <div class="card-body">
                            <h5 class="card-title"><i class="fas fa-map-marker-alt"></i> High Location Coverage</h5>
                            <h2 class="mb-0">${currentKpiData.high_location_coverage_employees.count || 0} Employees</h2>
                            <small>Visited > ${currentKpiData.high_location_coverage_employees.threshold || 3} floors today</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);">
                        <div class="card-body">
                            <h5 class="card-title"><i class="fas fa-exclamation-triangle"></i> High Outside Time Employees</h5>
                            <h2 class="mb-0">${currentKpiData.high_outside_employees.count || 0} Employees</h2>
                            <small>${currentKpiData.high_outside_employees.percentage || 0}% above ${currentKpiData.high_outside_employees.threshold || 0}min avg</small>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Insert the KPI cards into the container
        kpiContainer.innerHTML = kpiCardsHtml;
    } else {
        // This is the old KPI format - use existing rendering
        const kpiCardsHtml = `
            <div class="row mb-4">
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #0d6efd 0%, #0b5ed7 100%);">
                        <div class="card-body">
                            <h5 class="card-title"><i class="fas fa-users"></i> Total Employees</h5>
                            <h2 class="mb-0">${currentKpiData.TOTAL_EMPLOYEES || 0}</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #198754 0%, #157347 100%);">
                        <div class="card-body">
                            <h5 class="card-title"><i class="fas fa-fingerprint"></i> Total Hits</h5>
                            <h2 class="mb-0">${currentKpiData.TOTAL_HITS || 0}</h2>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #0dcaf0 0%, #3dd5f3 100%);">
                        <div class="card-body">
                            <h5 class="card-title"><i class="fas fa-clock"></i> Avg Presence (Hrs)</h5>
                            <h2 class="mb-0">${(currentKpiData.AVG_PRESENCE_DURATION || 0).toFixed(2)}</h2>
                        </div>
                    </div>
                </div>
            </div>
            <div class="row mb-4">
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #fd7e14 0%, #fd9248 100%);">
                        <div class="card-body">
                            <h5 class="card-title"><i class="fas fa-user-clock"></i> Longest Presence (in hrs.)</h5>
                            <h2 class="mb-0">${(currentKpiData.MAX_PRESENCE_DURATION || 0).toFixed(2)}</h2>
                            <small>${currentKpiData.LONGEST_PRESENCE_EMPLOYEE || 'N/A'}</small>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #6f42c1 0%, #7d5da8 100%);">
                        <div class="card-body">
                            <h5 class="card-title"><i class="fas fa-building"></i> Multi-Floor Emp</h5>
                            <h2 class="mb-0">${currentKpiData.MULTI_FLOOR_EMPLOYEES || 0}</h2>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Insert the KPI cards into the container
        kpiContainer.innerHTML = kpiCardsHtml;
    }
}

// Show a specific view and hide others
function showView(viewName) {
    if (!checkAuth()) return;
        
    // Hide all views
    if (dashboardView) dashboardView.classList.add('d-none');
    if (camerasView) camerasView.classList.add('d-none');
    if (summaryView) summaryView.classList.add('d-none');
    if (downtimeView) downtimeView.classList.add('d-none');
    if (addCameraView) addCameraView.classList.add('d-none');
    if (updateCameraStatusView) updateCameraStatusView.classList.add('d-none');
    if (employeeMovementView) employeeMovementView.classList.add('d-none');
    if (registeredUsersView) registeredUsersView.classList.add('d-none');
    if (dailyInOutSummaryView) dailyInOutSummaryView.classList.add('d-none');
    if (locationCoverageView) locationCoverageView.classList.add('d-none');
        
    // Use the centralized active state management if available
    if (typeof handleNavigation === 'function') {
        handleNavigation(viewName);
    }
        
    // Show the selected view
    if (viewName === 'dashboard') {
        if (dashboardView) dashboardView.classList.remove('d-none');
    } else if (viewName === 'cameras') {
        if (camerasView) camerasView.classList.remove('d-none');
        // Load camera data if not already loaded
        if (camerasTableBody && camerasTableBody.innerHTML.trim() === '') {
            // Add loading state
            const cameraCard = document.querySelector('#cameras-view .card');
            if (cameraCard) {
                cameraCard.classList.add('btn-loading');
            }
                
            fetchCameras().finally(() => {
                // Remove loading state
                if (cameraCard) {
                    cameraCard.classList.remove('btn-loading');
                }
            });
        }
    } else if (viewName === 'summary') {
        if (summaryView) summaryView.classList.remove('d-none');
        // Load summary data if not already loaded
        if (summaryTableBody && (summaryTableBody.innerHTML.trim() === '' || summaryTableBody.innerHTML.includes('No employee data found'))) {
            // Clear cache to ensure fresh data is fetched
            aggregatedDataCache = {};
                
            // Add loading state
            const summaryCard = document.querySelector('#summary-view .card');
            if (summaryCard) {
                summaryCard.classList.add('btn-loading');
            }
                
            Promise.all([
                fetchEmployeeSummary(fromDateEl.value, toDateEl.value),
                fetchEmployeeSummaryAggregated(fromDateEl.value, toDateEl.value)
            ]).finally(() => {
                // Remove loading state
                if (summaryCard) {
                    summaryCard.classList.remove('btn-loading');
                }
            });
        } else {
            // Even if data is already loaded, ensure KPI is rendered
            // Use a small delay to ensure DOM is updated before rendering
            setTimeout(() => {
                // Check if aggregated data is available, if not, fetch it
                if (!currentKpiData || Object.keys(currentKpiData).length === 0 || 
                    !currentChartData || !currentChartData.department_data || !currentChartData.entry_time_data) {
                    fetchEmployeeSummaryAggregated(fromDateEl.value, toDateEl.value);
                } else {
                    renderKpiCards();
                }
            }, 50); // Small delay to ensure DOM is updated
        }
    } else if (viewName === 'downtime') {
        if (downtimeView) downtimeView.classList.remove('d-none');
        // Load downtime data if not already loaded
        if (downtimeTableBody && (downtimeTableBody.innerHTML.trim() === '' || downtimeTableBody.innerHTML.includes('No downtime data found'))) {
            // Add loading state
            const downtimeCard = document.querySelector('#downtime-view .card');
            if (downtimeCard) {
                downtimeCard.classList.add('btn-loading');
            }
                
            // Use downtime-specific date fields if available, otherwise fall back to global ones
            const fromField = downtimeFromDateEl && downtimeFromDateEl.value ? downtimeFromDateEl : fromDateEl;
            const toField = downtimeToDateEl && downtimeToDateEl.value ? downtimeToDateEl : toDateEl;
            
            // Load employee downtime data
            fetchDowntimeSummary(fromField.value, toField.value).finally(() => {
                // Remove loading state
                if (downtimeCard) {
                    downtimeCard.classList.remove('btn-loading');
                }
            });
        }
    } else if (viewName === 'employee-movement') {
        if (employeeMovementView) {
            employeeMovementView.classList.remove('d-none');
                
            // Set default date values for employee movement
            const today = new Date();
            const todayStr = today.toISOString().split('T')[0];
            const from_date = document.getElementById('from_date');
            const to_date = document.getElementById('to_date');
            if (from_date) from_date.value = todayStr;
            if (to_date) to_date.value = todayStr;
        }
    } else if (viewName === 'face-recognition') {
        // For face recognition, we just show the active state on the link
        // The actual redirection happens in the click handler
    } else if (viewName === 'add-camera') {
        if (addCameraView) addCameraView.classList.remove('d-none');
        // Redirect to the dedicated add camera page
        window.location.href = 'add_camera.html';
    } else if (viewName === 'update-camera-status') {
        if (updateCameraStatusView) updateCameraStatusView.classList.remove('d-none');
        // Redirect to the dedicated update camera status page
        window.location.href = 'update_camera_status.html';
    } else if (viewName === 'registered-users') {
        if (registeredUsersView) registeredUsersView.classList.remove('d-none');
        // Load registered users data if not already loaded
        if (registeredUsersTableBody && (registeredUsersTableBody.innerHTML.trim() === '' || 
            registeredUsersTableBody.innerHTML.includes('No registered users found') ||
            registeredUsersTableBody.innerHTML.includes('Loading...'))) {
            fetchRegisteredUsers();
        }
    } else if (viewName === 'daily-inout-summary') {
        if (dailyInOutSummaryView) {
            dailyInOutSummaryView.classList.remove('d-none');
            
            // Set default date values for daily IN/OUT summary
            const today = new Date();
            const todayStr = today.toISOString().split('T')[0];
            const inout_from_date = document.getElementById('inout_from_date');
            const inout_to_date = document.getElementById('inout_to_date');
            if (inout_from_date) inout_from_date.value = todayStr;
            if (inout_to_date) inout_to_date.value = todayStr;
        }
    } else if (viewName === 'location-coverage') {
        if (locationCoverageView) {
            locationCoverageView.classList.remove('d-none');
            
            // Set default date values for location coverage report
            const today = new Date();
            const todayStr = today.toISOString().split('T')[0];
            const lc_from_date = document.getElementById('lc_from_date');
            const lc_to_date = document.getElementById('lc_to_date');
            const lc_employee_id = document.getElementById('lc_employee_id');
            if (lc_from_date) lc_from_date.value = todayStr;
            if (lc_to_date) lc_to_date.value = todayStr;
            if (lc_employee_id) lc_employee_id.value = '';
        }
    }
}

// Redirect to face recognition system
async function redirectToFaceRecognition() {
    if (!checkAuth()) return;
    
    try {
        // Show loading indicator
        const originalHTML = faceRecognitionLink.innerHTML;
        faceRecognitionLink.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Opening...';
        faceRecognitionLink.classList.add('btn-loading');
        
        const response = await fetch(`${API_BASE_URL}/face-recognition-url`);
        const result = await response.json();
        
        if (result.success) {
            // Open the face recognition system in a new tab
            const newWindow = window.open(result.url, '_blank');
            
            // Check if popup was blocked
            if (!newWindow || newWindow.closed || typeof newWindow.closed === 'undefined') {
                showAlert('Popup was blocked by your browser. Please allow popups for this site and try again.', 'warning');
                faceRecognitionLink.innerHTML = originalHTML;
                faceRecognitionLink.classList.remove('btn-loading');
                return;
            }
            
            // Success message
            showAlert('Face recognition system opened in a new tab', 'success');
        } else {
            showAlert('Failed to get face recognition URL: ' + result.error, 'danger');
        }
        
        // Restore original button text
        faceRecognitionLink.innerHTML = originalHTML;
        faceRecognitionLink.classList.remove('btn-loading');
    } catch (error) {
        showAlert('Error connecting to face recognition system: ' + error.message, 'danger');
        // Restore original button text
        faceRecognitionLink.innerHTML = '<i class="fas fa-user-check"></i> Face Recognition';
        faceRecognitionLink.classList.remove('btn-loading');
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', function() {
    // Check authentication first
    if (!checkAuth()) return;
    
    // Set default dates
    setDefaultDates();
    
    // Load initial data
    // Add loading state to dashboard KPIs
    const kpiContainer = document.querySelector('#kpi-cards-container');
    if (kpiContainer) {
        kpiContainer.innerHTML = `
            <div class="row mb-4">
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
                        <div class="card-body text-center">
                            <div class="spinner-border text-light" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2 mb-0">Loading...</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
                        <div class="card-body text-center">
                            <div class="spinner-border text-light" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2 mb-0">Loading...</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
                        <div class="card-body text-center">
                            <div class="spinner-border text-light" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2 mb-0">Loading...</p>
                        </div>
                    </div>
                </div>
            </div>
            <div class="row mb-4">
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
                        <div class="card-body text-center">
                            <div class="spinner-border text-light" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2 mb-0">Loading...</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
                        <div class="card-body text-center">
                            <div class="spinner-border text-light" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2 mb-0">Loading...</p>
                        </div>
                    </div>
                </div>
                <div class="col-md-4 mb-3">
                    <div class="card text-white" style="background: linear-gradient(135deg, #6c757d 0%, #495057 100%);">
                        <div class="card-body text-center">
                            <div class="spinner-border text-light" role="status">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                            <p class="mt-2 mb-0">Loading...</p>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Fetch the new dashboard KPIs
    const today = new Date().toISOString().split('T')[0];
    fetchNewDashboardKpis(today, today).finally(() => {
        // Remove loading state is handled in the fetchNewDashboardKpis function
    });
    
    // Sidebar navigation
    dashboardLink.addEventListener('click', function(e) {
        e.preventDefault();
        showView('dashboard');
    });
    
    // Reports dropdown toggle - removed manual handling since we're using Bootstrap's collapse
    
    // Report links (employee summary, downtime summary, etc.)
    reportLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const viewName = this.id.replace('-link', '');
            showView(viewName);
        });
    });
    
    // Drishti Management links (camera registry, registered users, and face recognition)
    const drishtiManagementLinks = document.querySelectorAll('.drishti-management-link');
    drishtiManagementLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const viewName = this.id.replace('-link', '');
            showView(viewName);
            
            // Ensure Drishti Management dropdown stays open
            const drishtiManagementSubmenu = document.getElementById('drishti-management-submenu');
            if (drishtiManagementSubmenu && !drishtiManagementSubmenu.classList.contains('show')) {
                drishtiManagementSubmenu.classList.add('show');
                if (drishtiManagementDropdown) {
                    drishtiManagementDropdown.setAttribute('aria-expanded', 'true');
                }
            }
        });
    });
    
    // Face recognition link - improved event handler
    if (faceRecognitionLink) {
        faceRecognitionLink.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation(); // Prevent event bubbling
            showView('face-recognition');
            redirectToFaceRecognition();
            return false;
        });
    }
    
    // Reports dropdown click handler
    reportsDropdown.addEventListener('click', function(e) {
        // Just toggle the dropdown, don't change the active state of other items
        // The active state should remain on the currently selected item
        e.stopPropagation();
    });
    
    // Add Camera link
    if (addCameraLink) {
        addCameraLink.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            showView('add-camera');
        });
    }
    
    // Update Camera Status link
    if (updateCameraStatusLink) {
        updateCameraStatusLink.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            showView('update-camera-status');
        });
    }
    
    // Drishti Management dropdown click handler
    if (drishtiManagementDropdown) {
        drishtiManagementDropdown.addEventListener('click', function(e) {
            // Just toggle the dropdown, don't change the active state of other items
            // The active state should remain on the currently selected item
            e.stopPropagation();
        });
    }
    
    // Camera Management dropdown click handler
    const cameraManagementDropdown = document.getElementById('camera-management-dropdown');
    if (cameraManagementDropdown) {
        cameraManagementDropdown.addEventListener('click', function(e) {
            // Ensure Drishti Management dropdown stays open when clicking on Camera Management
            const drishtiManagementSubmenu = document.getElementById('drishti-management-submenu');
            if (drishtiManagementSubmenu && !drishtiManagementSubmenu.classList.contains('show')) {
                drishtiManagementSubmenu.classList.add('show');
                const localDrishtiManagementDropdown = document.getElementById('drishti-management-dropdown');
                if (localDrishtiManagementDropdown) {
                    localDrishtiManagementDropdown.setAttribute('aria-expanded', 'true');
                }
            }
            
            // Just toggle the dropdown, don't change the active state of other items
            // The active state should remain on the currently selected item
            e.stopPropagation();
        });
    }
    
    // Camera Info links (both add camera and update camera status)
    cameraInfoLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Ensure Drishti Management dropdown stays open
            const drishtiManagementSubmenu = document.getElementById('drishti-management-submenu');
            if (drishtiManagementSubmenu && !drishtiManagementSubmenu.classList.contains('show')) {
                drishtiManagementSubmenu.classList.add('show');
                const localDrishtiManagementDropdown = document.getElementById('drishti-management-dropdown');
                if (localDrishtiManagementDropdown) {
                    localDrishtiManagementDropdown.setAttribute('aria-expanded', 'true');
                }
            }
            
            const viewName = this.id.replace('-link', '');
            showView(viewName);
        });
    })
    
    // Refresh buttons
    if (refreshCamerasBtn) {
        refreshCamerasBtn.addEventListener('click', function() {
            // Add loading state
            const originalHTML = refreshCamerasBtn.innerHTML;
            refreshCamerasBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            refreshCamerasBtn.classList.add('btn-loading');
            
            // Fetch data
            fetchCameras().finally(() => {
                // Remove loading state
                refreshCamerasBtn.innerHTML = originalHTML;
                refreshCamerasBtn.classList.remove('btn-loading');
            });
        });
    }
    
    if (refreshSummaryBtn) {
        refreshSummaryBtn.addEventListener('click', function() {
            // Clear cache to ensure fresh data is fetched
            aggregatedDataCache = {};
            
            // Add loading state
            const originalHTML = refreshSummaryBtn.innerHTML;
            refreshSummaryBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            refreshSummaryBtn.classList.add('btn-loading');
            
            // Fetch data
            if (fromDateEl && toDateEl) {
                Promise.all([
                    fetchEmployeeSummary(fromDateEl.value, toDateEl.value),
                    fetchEmployeeSummaryAggregated(fromDateEl.value, toDateEl.value)
                ]).finally(() => {
                    // Remove loading state
                    refreshSummaryBtn.innerHTML = originalHTML;
                    refreshSummaryBtn.classList.remove('btn-loading');
                });
            }
        });
    }
    
    if (refreshDowntimeBtn) {
        refreshDowntimeBtn.addEventListener('click', function() {
            // Add loading state
            const originalHTML = refreshDowntimeBtn.innerHTML;
            refreshDowntimeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            refreshDowntimeBtn.classList.add('btn-loading');
            
            // Fetch employee downtime data
            // Use downtime-specific date fields if available, otherwise fall back to global ones
            const fromField = downtimeFromDateEl && downtimeFromDateEl.value ? downtimeFromDateEl : fromDateEl;
            const toField = downtimeToDateEl && downtimeToDateEl.value ? downtimeToDateEl : toDateEl;
            
            if (fromField && toField) {
                fetchDowntimeSummary(fromField.value, toField.value).finally(() => {
                    // Remove loading state
                    refreshDowntimeBtn.innerHTML = originalHTML;
                    refreshDowntimeBtn.classList.remove('btn-loading');
                });
            }
        });
    }
    
    // Apply filter button
    if (applyFilterBtn && fromDateEl && toDateEl) {
        applyFilterBtn.addEventListener('click', () => {
            if (fromDateEl.value && toDateEl.value) {
                // Clear cache to ensure fresh data is fetched
                aggregatedDataCache = {};
                
                // Add loading state
                const originalHTML = applyFilterBtn.innerHTML;
                applyFilterBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Applying...';
                applyFilterBtn.classList.add('btn-loading');
                
                // Fetch data for all relevant views
                Promise.all([
                    fetchEmployeeSummary(fromDateEl.value, toDateEl.value),
                    fetchDowntimeSummary(fromDateEl.value, toDateEl.value),
                    fetchEmployeeSummaryAggregated(fromDateEl.value, toDateEl.value)
                ]).finally(() => {
                    // Remove loading state
                    applyFilterBtn.innerHTML = originalHTML;
                    applyFilterBtn.classList.remove('btn-loading');
                });
            } else {
                showAlert('Please select both from and to dates', 'warning');
            }
        });
    }
    
    // Apply downtime filter button
    if (applyDowntimeFilterBtn && downtimeFromDateEl && downtimeToDateEl) {
        applyDowntimeFilterBtn.addEventListener('click', () => {
            if (downtimeFromDateEl.value && downtimeToDateEl.value) {
                // Add loading state
                const originalHTML = applyDowntimeFilterBtn.innerHTML;
                applyDowntimeFilterBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Applying...';
                applyDowntimeFilterBtn.classList.add('btn-loading');
                
                // Fetch downtime data with new date range
                fetchDowntimeSummary(downtimeFromDateEl.value, downtimeToDateEl.value).finally(() => {
                    // Remove loading state
                    applyDowntimeFilterBtn.innerHTML = originalHTML;
                    applyDowntimeFilterBtn.classList.remove('btn-loading');
                });
            } else {
                showAlert('Please select both from and to dates', 'warning');
            }
        });
    }
    
    // Search input event listeners
    if (summarySearchEl) {
        summarySearchEl.addEventListener('input', () => {
            applySearchFilter();
            renderEmployeeSummary(filteredSummaryData);
        });
    }
    
    if (downtimeSearchEl) {
        downtimeSearchEl.addEventListener('input', () => {
            applyDowntimeSearchFilter();
            renderDowntimeSummary(filteredDowntimeData);
        });
    }
    

    // Registered users search input event listener
    if (registeredUsersSearchEl) {
        registeredUsersSearchEl.addEventListener('input', () => {
            applyRegisteredUsersSearchFilter();
        });
    }
    
    // Refresh registered users button
    if (refreshRegisteredUsersBtn) {
        refreshRegisteredUsersBtn.addEventListener('click', function() {
            // Add loading state
            const originalHTML = refreshRegisteredUsersBtn.innerHTML;
            refreshRegisteredUsersBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            refreshRegisteredUsersBtn.classList.add('btn-loading');
            
            // Fetch data
            fetchRegisteredUsers().finally(() => {
                // Remove loading state
                refreshRegisteredUsersBtn.innerHTML = originalHTML;
                refreshRegisteredUsersBtn.classList.remove('btn-loading');
            });
        });
    }
    
    // Sort option event listeners for employee summary
    const sortOptions = document.querySelectorAll('.sort-option');
    if (sortOptions.length > 0) {
        sortOptions.forEach(option => {
            option.addEventListener('click', (e) => {
                e.preventDefault();
                const column = e.target.getAttribute('data-sort');
                const direction = e.target.getAttribute('data-dir');
                
                currentSort = { column, direction };
                sortData(column, direction);
                renderEmployeeSummary(filteredSummaryData);
                
                // Update button text to show current sort
                const sortButton = document.querySelector('#sortDropdown');
                if (sortButton) {
                    sortButton.innerHTML = `<i class="fas fa-sort"></i> Sorted by ${e.target.textContent}`;
                }
            });
        });
    }
    
    // Sort option event listeners for downtime summary
    const downtimeSortOptions = document.querySelectorAll('.downtime-sort-option');
    if (downtimeSortOptions.length > 0) {
        downtimeSortOptions.forEach(option => {
            option.addEventListener('click', (e) => {
                e.preventDefault();
                const column = e.target.getAttribute('data-sort');
                const direction = e.target.getAttribute('data-dir');
                
                currentSort = { column, direction };
                sortDowntimeData(column, direction);
                renderDowntimeSummary(filteredDowntimeData);
                
                // Update button text to show current sort
                const sortButton = document.querySelector('#downtimeSortDropdown');
                if (sortButton) {
                    sortButton.innerHTML = `<i class="fas fa-sort"></i> Sorted by ${e.target.textContent}`;
                }
            });
        });
    }
    

    // Sort function for registered users
    function sortRegisteredUsers(column, direction) {
        currentRegisteredUsersData.sort((a, b) => {
            let aValue = a[column];
            let bValue = b[column];
            
            // Handle numeric sorting
            if (column === 'ID' || column === 'EMPLOYEE_ID') {
                aValue = parseFloat(aValue) || 0;
                bValue = parseFloat(bValue) || 0;
            }
            
            // Handle date sorting
            if (column === 'CREATED_DATE') {
                aValue = new Date(aValue);
                bValue = new Date(bValue);
            }
            
            // Handle string sorting
            if (typeof aValue === 'string') {
                aValue = aValue.toLowerCase();
                bValue = bValue.toLowerCase();
            }
            
            if (direction === 'asc') {
                return aValue > bValue ? 1 : aValue < bValue ? -1 : 0;
            } else {
                return aValue < bValue ? 1 : aValue > bValue ? -1 : 0;
            }
        });
    }
    
    // Sort option event listeners for registered users
    const registeredUsersSortOptions = document.querySelectorAll('.registered-users-sort-option');
    if (registeredUsersSortOptions.length > 0) {
        registeredUsersSortOptions.forEach(option => {
            option.addEventListener('click', (e) => {
                e.preventDefault();
                const column = e.target.getAttribute('data-sort');
                const direction = e.target.getAttribute('data-dir');
                
                currentSort = { column, direction };
                sortRegisteredUsers(column, direction);
                renderRegisteredUsers(currentRegisteredUsersData);
                
                // Update button text to show current sort
                const sortButton = document.querySelector('#registeredUsersSortDropdown');
                if (sortButton) {
                    sortButton.innerHTML = `<i class="fas fa-sort"></i> Sorted by ${e.target.textContent}`;
                }
            });
        });
    }
    
    // User Management dropdown click handler (nested under Drishti Management)
    const userManagementDropdown = document.getElementById('user-management-dropdown');
    if (userManagementDropdown) {
        userManagementDropdown.addEventListener('click', function(e) {
            // Just toggle the dropdown, don't change the active state of other items
            // The active state should remain on the currently selected item
            e.stopPropagation();
        });
    }
    
    // User Management links
    const userManagementLinks = document.querySelectorAll('.user-management-link');
    userManagementLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            // Redirect to user management page with appropriate hash
            const href = this.getAttribute('href');
            // Extract just the hash part in case the full URL is returned
            const hash = href.includes('#') ? href.substring(href.indexOf('#')) : '';
            
            // Ensure Drishti Management dropdown stays open
            const drishtiManagementSubmenu = document.getElementById('drishti-management-submenu');
            if (drishtiManagementSubmenu && !drishtiManagementSubmenu.classList.contains('show')) {
                drishtiManagementSubmenu.classList.add('show');
                if (drishtiManagementDropdown) {
                    drishtiManagementDropdown.setAttribute('aria-expanded', 'true');
                }
            }
            
            window.location.href = 'user_management.html' + hash;
        });
    });
    
    // Admin Access Control link (special case - goes to separate page)
    const adminAccessControlLink = document.getElementById('admin-access-control-link');
    if (adminAccessControlLink) {
        adminAccessControlLink.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            
            // Ensure Drishti Management dropdown stays open
            const drishtiManagementSubmenu = document.getElementById('drishti-management-submenu');
            if (drishtiManagementSubmenu && !drishtiManagementSubmenu.classList.contains('show')) {
                drishtiManagementSubmenu.classList.add('show');
                if (drishtiManagementDropdown) {
                    drishtiManagementDropdown.setAttribute('aria-expanded', 'true');
                }
            }
            
            // Redirect to admin access control page
            window.location.href = 'admin_access_control.html';
        });
    }
    
    // Sidebar toggle functionality
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            
            // Change icon based on sidebar state
            const icon = sidebarToggle.querySelector('i');
            if (sidebar.classList.contains('collapsed')) {
                icon.classList.remove('fa-bars');
                icon.classList.add('fa-times');
            } else {
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
            }
            
            // Trigger a resize event to ensure proper layout adjustment
            window.dispatchEvent(new Event('resize'));
        });
    }
    
    // Handle window resize to update charts
    window.addEventListener('resize', function() {
        // Update charts when window is resized to maintain responsiveness
        if (window.departmentChartInstance) {
            setTimeout(() => {
                window.departmentChartInstance.update();
            }, 100);
        }
        
        if (window.entryTimeChartInstance) {
            setTimeout(() => {
                window.entryTimeChartInstance.update();
            }, 100);
        }
    });
    
    // Check for hash in URL to determine which view to show
    const hash = window.location.hash;
    if (hash === '#cameras') {
        showView('cameras');
    } else if (hash === '#summary') {
        showView('summary');
    } else if (hash === '#downtime') {
        showView('downtime');
    } else if (hash === '#employee-movement') {
        showView('employee-movement');
    } else if (hash === '#daily-inout-summary') {
        showView('daily-inout-summary');
    } else if (hash === '#registered-users') {
        showView('registered-users');
    } else {
        // Show dashboard view by default
        showView('dashboard');
    }
    
    // Ensure Drishti Management dropdown remains expanded when navigating to nested items
    // Expand Drishti Management dropdown if any of its child items are active
    const drishtiManagementSubmenu = document.getElementById('drishti-management-submenu');
    if (drishtiManagementSubmenu) {
        const currentPath = window.location.pathname.split('/').pop();
        const userManagementPages = ['user_management.html', 'admin_access_control.html'];
        const cameraManagementPages = ['add_camera.html', 'update_camera_status.html'];
        
        // Check if we're on a page that should expand the Drishti Management dropdown
        if (userManagementPages.includes(currentPath) || cameraManagementPages.includes(currentPath) || hash.includes('registered-users') || hash.includes('cameras')) {
            drishtiManagementSubmenu.classList.add('show');
            if (drishtiManagementDropdown) {
                drishtiManagementDropdown.setAttribute('aria-expanded', 'true');
            }
        }
    }
    
    // Handle employee movement form submission
    const movementTrackingForm = document.getElementById('movement-tracking-form');
    if (movementTrackingForm) {
        movementTrackingForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const employeeId = document.getElementById('employee_id').value.trim();
            const fromDate = document.getElementById('from_date').value;
            const toDate = document.getElementById('to_date').value || new Date().toISOString().split('T')[0];
            
            if (!fromDate) {
                showAlert('Please enter required field (From Date)', 'warning');
                return;
            }
            
            // Show loading state
            const submitBtn = document.getElementById('track-movement-btn');
            const originalHtml = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Tracking Movement...';
            submitBtn.disabled = true;
            
            try {
                // Call the API to get movement data
                let url = `${API_BASE_URL}/employee-movement?from_date=${fromDate}&to_date=${toDate}`;
                if (employeeId) {
                    url += `&employee_id=${employeeId}`;
                }
                const response = await fetch(url);
                const result = await response.json();
                
                if (result.success) {
                    renderMovementData(result.data);
                } else {
                    movementTableBody.innerHTML = `<tr><td colspan="12" class="text-center text-danger">Error: ${result.error || 'Unknown error'}</td></tr>`;
                    showAlert(`Failed to get movement data: ${result.error || 'Unknown error'}`, 'danger');
                }
            } catch (error) {
                movementTableBody.innerHTML = `<tr><td colspan="12" class="text-center text-danger">Error: ${error.message}</td></tr>`;
                showAlert(`Error getting movement data: ${error.message}`, 'danger');
                console.error('Error:', error);
            } finally {
                // Restore button state
                submitBtn.innerHTML = originalHtml;
                submitBtn.disabled = false;
            }
        });
    }
    
    // Refresh movement data button
    if (refreshMovementBtn) {
        refreshMovementBtn.addEventListener('click', function() {
            document.getElementById('movement-tracking-form').dispatchEvent(new Event('submit'));
        });
    }
    
    // Export functionality
    const exportExcelBtn = document.getElementById('export-excel');
    if (exportExcelBtn) {
        exportExcelBtn.addEventListener('click', function(e) {
            e.preventDefault();
            exportMovementData('excel');
        });
    }
    
    const exportPdfBtn = document.getElementById('export-pdf');
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', function(e) {
            e.preventDefault();
            exportMovementData('pdf');
        });
    }
    
    // Function to export movement data
    function exportMovementData(format) {
        // Get current movement data from the table
        const table = document.getElementById('movement-table');
        if (!table || table.rows.length <= 1) {
            showAlert('No data to export', 'warning');
            return;
        }
        
        if (format === 'excel') {
            exportToExcel(table);
        } else if (format === 'pdf') {
            exportToPDF(table);
        }
    }
    
    // Function to export to Excel
    function exportToExcel(table) {
        // Check if SheetJS library is available
        if (typeof window.XLSX === 'undefined') {
            // If not available, show a message
            showAlert('Excel export requires SheetJS library. Please install it first.', 'warning');
            return;
        }
        
        try {
            const wb = window.XLSX.utils.table_to_book(table, {sheet: "Movement Data"});
            window.XLSX.writeFile(wb, "movement_tracking_data.xlsx");
            showAlert('Data exported to Excel successfully!', 'success');
        } catch (error) {
            showAlert('Error exporting to Excel: ' + error.message, 'danger');
            console.error('Excel export error:', error);
        }
    }
    
    // Function to export to PDF
    function exportToPDF(table) {
        // Check if jsPDF library is available
        let jsPdfLib = null;
        
        // Check different ways jsPDF might be exposed
        if (window.jspdf && window.jspdf.jsPDF) {
            jsPdfLib = window.jspdf;
        } else if (window.jsPDF) {
            jsPdfLib = { jsPDF: window.jsPDF };
        }
        
        if (!jsPdfLib) {
            showAlert('PDF export requires jsPDF library. Please install it first.', 'warning');
            return;
        }
        
        try {
            const pdf = new jsPdfLib.jsPDF();
            
            // Add title
            pdf.setFontSize(18);
            pdf.text('Movement Tracking Data', 20, 20);
            
            // Convert table to string format for PDF
            const colNames = [];
            const headers = table.querySelectorAll('thead th');
            headers.forEach(header => colNames.push(header.textContent));
            
            const data = [];
            const rows = table.querySelectorAll('tbody tr');
            rows.forEach(row => {
                const rowData = [];
                const cells = row.querySelectorAll('td');
                cells.forEach(cell => rowData.push(cell.textContent));
                data.push(rowData);
            });
            
            // Add table content using autoTable plugin if available
            if (typeof pdf.autoTable !== 'undefined') {
                pdf.autoTable({
                    head: [colNames],
                    body: data,
                    startY: 30,
                    theme: 'grid',
                    headStyles: { fillColor: [13, 110, 253] } // Bootstrap primary blue
                });
                
                pdf.save('movement_tracking_data.pdf');
                showAlert('Data exported to PDF successfully!', 'success');
            } else {
                // Fallback: simple text-based PDF
                let yPosition = 40;
                colNames.forEach((header, index) => {
                    pdf.text(header, 10 + (index * 25), yPosition);
                });
                
                yPosition += 10;
                data.forEach(row => {
                    row.forEach((cell, index) => {
                        pdf.text(cell, 10 + (index * 25), yPosition);
                    });
                    yPosition += 10;
                    if (yPosition > 280) { // Reset position if near bottom
                        pdf.addPage();
                        yPosition = 20;
                    }
                });
                
                pdf.save('movement_tracking_data.pdf');
                showAlert('Data exported to PDF (basic format) successfully!', 'success');
            }
        } catch (error) {
            showAlert('Error exporting to PDF: ' + error.message, 'danger');
            console.error('PDF export error:', error);
        }
    }
    
    // Daily IN/OUT Summary form submission
    const inoutSummaryForm = document.getElementById('inout-summary-form');
    if (inoutSummaryForm) {
        inoutSummaryForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const employeeId = document.getElementById('inout_employee_id').value.trim();
            const fromDate = document.getElementById('inout_from_date').value;
            const toDate = document.getElementById('inout_to_date').value || new Date().toISOString().split('T')[0];
            
            if (!fromDate) {
                showAlert('Please enter required field (From Date)', 'warning');
                return;
            }
            
            // Show loading state
            const submitBtn = document.getElementById('get-inout-summary-btn');
            const originalHtml = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Getting IN/OUT Summary...';
            submitBtn.disabled = true;
            
            try {
                // Call the API to get IN/OUT summary data
                await fetchInOutSummary(employeeId, fromDate, toDate);
            } catch (error) {
                inoutSummaryTableBody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">Error: ${error.message}</td></tr>`;
                showAlert(`Error getting IN/OUT summary: ${error.message}`, 'danger');
                console.error('Error:', error);
            } finally {
                // Restore button state
                submitBtn.innerHTML = originalHtml;
                submitBtn.disabled = false;
            }
        });
    }
    
    // Refresh IN/OUT Summary data button
    if (refreshInOutSummaryBtn) {
        refreshInOutSummaryBtn.addEventListener('click', function() {
            const inoutSummaryForm = document.getElementById('inout-summary-form');
            if (inoutSummaryForm) {
                inoutSummaryForm.dispatchEvent(new Event('submit'));
            }
        });
    }
    
    // Export functionality for IN/OUT Summary
    const exportInOutExcelBtn = document.getElementById('export-inout-excel');
    if (exportInOutExcelBtn) {
        exportInOutExcelBtn.addEventListener('click', function(e) {
            e.preventDefault();
            exportInOutSummaryData('excel');
        });
    }
    
    const exportInOutPdfBtn = document.getElementById('export-inout-pdf');
    if (exportInOutPdfBtn) {
        exportInOutPdfBtn.addEventListener('click', function(e) {
            e.preventDefault();
            exportInOutSummaryData('pdf');
        });
    }
    
    // Function to export IN/OUT summary data
    function exportInOutSummaryData(format) {
        // Get current IN/OUT summary data from the table
        const table = document.getElementById('inout-summary-table');
        if (!table || table.rows.length <= 1) {
            showAlert('No data to export', 'warning');
            return;
        }
        
        if (format === 'excel') {
            exportToExcel(table);
        } else if (format === 'pdf') {
            exportToPDF(table);
        }
    }
    
    // Location Coverage Report form submission
    const locationCoverageForm = document.getElementById('location-coverage-form');
    if (locationCoverageForm) {
        locationCoverageForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const employeeId = document.getElementById('lc_employee_id').value.trim();
            const fromDate = document.getElementById('lc_from_date').value;
            const toDate = document.getElementById('lc_to_date').value || new Date().toISOString().split('T')[0];
            
            if (!fromDate) {
                showAlert('Please enter required field (From Date)', 'warning');
                return;
            }
            
            // Show loading state
            const submitBtn = document.getElementById('get-location-coverage-btn');
            const originalHtml = submitBtn.innerHTML;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Getting Location Coverage Report...';
            submitBtn.disabled = true;
            
            try {
                // Call the API to get location coverage data
                let url = `${API_BASE_URL}/location-coverage-report?from_date=${fromDate}&to_date=${toDate}`;
                if (employeeId) {
                    url += `&employee_id=${employeeId}`;
                }
                const response = await fetch(url);
                const result = await response.json();
                
                if (result.success) {
                    renderLocationCoverageData(result.data);
                } else {
                    const locationCoverageTableBody = document.querySelector('#location-coverage-table tbody');
                    if (locationCoverageTableBody) {
                        locationCoverageTableBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Error: ${result.error || 'Unknown error'}</td></tr>`;
                    }
                    showAlert(`Failed to get location coverage data: ${result.error || 'Unknown error'}`, 'danger');
                }
            } catch (error) {
                const locationCoverageTableBody = document.querySelector('#location-coverage-table tbody');
                if (locationCoverageTableBody) {
                    locationCoverageTableBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Error: ${error.message}</td></tr>`;
                }
                showAlert(`Error getting location coverage data: ${error.message}`, 'danger');
                console.error('Error:', error);
            } finally {
                // Restore button state
                submitBtn.innerHTML = originalHtml;
                submitBtn.disabled = false;
            }
        });
    }
    
    // Function to render location coverage data
    function renderLocationCoverageData(coverageData) {
        const locationCoverageTableBody = document.querySelector('#location-coverage-table tbody');
        
        if (!locationCoverageTableBody) {
            console.error('Location coverage table body not found');
            return;
        }
        
        if (!coverageData || coverageData.length === 0) {
            locationCoverageTableBody.innerHTML = '<tr><td colspan="7" class="text-center">No location coverage data found</td></tr>';
            return;
        }
        
        let html = '';
        coverageData.forEach(record => {
            html += `
                <tr>
                    <td>${record.REC_DATE ? new Date(record.REC_DATE).toLocaleDateString() : '-'}</td>
                    <td>${record.EMPLOYEE_ID || '-'}</td>
                    <td>${record.NAME || '-'}</td>
                    <td>${record.DEPARTMENT || '-'}</td>
                    <td>${record.UNIQUE_FLOORS_VISITED || 0}</td>
                    <td>${record.UNIQUE_LOCATIONS_VISITED || 0}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="openLocationCoverageDetails('${record.EMPLOYEE_ID}', '${record.REC_DATE ? String(record.REC_DATE).substring(0, 10) : ''}')">
                            <i class="fas fa-info-circle"></i> More Information
                        </button>
                    </td>
                </tr>
            `;
        });
        
        locationCoverageTableBody.innerHTML = html;
    }
    
    // Refresh location coverage data button
    const refreshLocationCoverageBtn = document.getElementById('refresh-location-coverage');
    if (refreshLocationCoverageBtn) {
        refreshLocationCoverageBtn.addEventListener('click', function() {
            const locationCoverageForm = document.getElementById('location-coverage-form');
            if (locationCoverageForm) {
                locationCoverageForm.dispatchEvent(new Event('submit'));
            }
        });
    }
    
    // Export functionality for Location Coverage Report
    const exportLocationCoverageExcelBtn = document.getElementById('export-location-coverage-excel');
    if (exportLocationCoverageExcelBtn) {
        exportLocationCoverageExcelBtn.addEventListener('click', function(e) {
            e.preventDefault();
            exportLocationCoverageData('excel');
        });
    }
    
    const exportLocationCoveragePdfBtn = document.getElementById('export-location-coverage-pdf');
    if (exportLocationCoveragePdfBtn) {
        exportLocationCoveragePdfBtn.addEventListener('click', function(e) {
            e.preventDefault();
            exportLocationCoverageData('pdf');
        });
    }
    

    
    // Function to export location coverage data
    function exportLocationCoverageData(format) {
        // Get current location coverage data from the table
        const table = document.getElementById('location-coverage-table');
        if (!table || table.rows.length <= 1) {
            showAlert('No data to export', 'warning');
            return;
        }
        
        if (format === 'excel') {
            exportToExcel(table);
        } else if (format === 'pdf') {
            exportToPDF(table);
        }
    }
    
    // Top Employee Movement Rankings functionality
    
    // DOM elements for rankings
    const rankingDateEl = document.getElementById('ranking-date');
    const rankingMetricEl = document.getElementById('ranking-metric');
    const rankingLimitEl = document.getElementById('ranking-limit');
    const refreshRankingsBtn = document.getElementById('refresh-rankings');
    const rankingsListEl = document.getElementById('rankings-list');
    
    // Set default date to yesterday
    function setDefaultRankingDate() {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        const yesterdayStr = yesterday.toISOString().split('T')[0];
        
        if (rankingDateEl) {
            rankingDateEl.value = yesterdayStr;
        }
    }
    
    // Fetch top employee movement rankings
    async function fetchTopEmployeeRankings(date, metric, limit) {
        if (!checkAuth()) return Promise.resolve();
        
        try {
            // Show loading state
            showRankingsLoading();
            
            const url = `${API_BASE_URL}/top-employee-movement?date=${date}&metric=${metric}&limit=${limit}`;
            const response = await fetch(url);
            const result = await response.json();
            
            if (result.success) {
                renderRankings(result.data);
            } else {
                showRankingsError('Failed to load rankings: ' + (result.error || 'Unknown error'));
                console.error('Failed to load rankings:', result.error);
            }
            return Promise.resolve();
        } catch (error) {
            console.error('Error loading rankings:', error);
            showRankingsError('Error loading rankings: ' + error.message);
            return Promise.reject(error);
        }
    }
    
    // Show loading state for rankings
    function showRankingsLoading() {
        if (rankingsListEl) {
            rankingsListEl.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-spinner fa-spin fa-2x text-muted mb-3"></i>
                    <p class="text-muted">Loading rankings...</p>
                </div>
            `;
        }
    }
    
    // Show error state for rankings
    function showRankingsError(message) {
        if (rankingsListEl) {
            rankingsListEl.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-exclamation-triangle fa-2x text-warning mb-3"></i>
                    <p class="text-muted">${message}</p>
                </div>
            `;
        }
    }
    
    // Render rankings list
    function renderRankings(rankings) {
        if (!rankingsListEl) return;
        
        if (!rankings || rankings.length === 0) {
            rankingsListEl.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-info-circle fa-2x text-muted mb-3"></i>
                    <p class="text-muted">No movement data available for selected date</p>
                </div>
            `;
            // Hide chart and show message
            const chartContainer = document.getElementById('rankings-chart-container');
            const chartCanvas = document.getElementById('rankings-bar-chart');
            if (chartContainer) chartContainer.style.display = 'none';
            if (rankingsListEl) rankingsListEl.classList.remove('d-none');
            return;
        }
        
        // Determine metric for display
        const isOutsideMetric = rankingMetricEl ? rankingMetricEl.value === 'outside' : true;
        const metricLabel = isOutsideMetric ? 'Outside' : 'Inside';
        const timeField = isOutsideMetric ? 'TOTAL_OUTSIDE_MINUTES' : 'TOTAL_INSIDE_MINUTES';
        
        // Prepare data for horizontal bar chart
        const labels = [];
        const data = [];
        
        rankings.forEach((item, index) => {
            const rank = index + 1;
            const employeeId = item.EMPLOYEE_ID || 'N/A';
            const name = item.NAME || 'Unknown';
            const time = item[timeField] || 0;
            
            // Create a truncated name for better readability on X-axis
            const truncatedName = truncateName(name);
            labels.push(`${rank}. ${employeeId} | ${truncatedName}`);
            data.push(time);
        });
        
        // Destroy existing chart if it exists
        if (window.rankingsChartInstance) {
            window.rankingsChartInstance.destroy();
        }
        
        // Calculate insights for the insight line
        const totalValue = data.reduce((sum, value) => sum + value, 0);
        const topTwoValue = data.length >= 2 ? data[0] + data[1] : data[0] || 0;
        const topThreeValue = data.length >= 3 ? data[0] + data[1] + data[2] : data.reduce((sum, value) => sum + value, 0);
        const topPercentage = totalValue > 0 ? ((topTwoValue / totalValue) * 100).toFixed(0) : 0;
        
        // Update insight text
        const insightElement = document.getElementById('rankings-insight-text');
        if (insightElement) {
            insightElement.textContent = `Top 2 employees account for ${topPercentage}% of total ${metricLabel.toLowerCase()} time`;
        }
        
        // Show chart container and hide list
        const chartContainer = document.getElementById('rankings-chart-container');
        const chartCanvas = document.getElementById('rankings-bar-chart');
        if (rankingsListEl) rankingsListEl.classList.add('d-none');
        if (chartContainer) chartContainer.style.display = 'block';
        
        // Set canvas dimensions
        chartCanvas.height = 400; // Fixed height for vertical bar chart
        
        // Create vertical bar chart
        const ctx = chartCanvas.getContext('2d');
        window.rankingsChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: `${metricLabel} Time (minutes)`,
                    data: data,
                    backgroundColor: data.map((value, index) => {
                        // Highlight the top-ranked bar (first item) with a stronger color
                        if (index === 0) {
                            return isOutsideMetric ? 'rgba(220, 53, 69, 1)' : 'rgba(40, 167, 69, 1)'; // Stronger color for rank #1
                        } else {
                            return isOutsideMetric ? 'rgba(220, 53, 69, 0.5)' : 'rgba(40, 167, 69, 0.5)'; // Lighter color for others
                        }
                    }),
                    borderColor: data.map((value, index) => {
                        // Same logic for border
                        if (index === 0) {
                            return isOutsideMetric ? 'rgb(220, 53, 69)' : 'rgb(40, 167, 69)';
                        } else {
                            return isOutsideMetric ? 'rgb(220, 53, 69)' : 'rgb(40, 167, 69)';
                        }
                    }),
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'x', // This makes it a vertical bar chart
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: `${metricLabel} Time (minutes)`
                        },
                        // Configure ticks to show round values only
                        ticks: {
                            // Ensure clean, round number intervals
                            callback: function(value) {
                                // Only show round numbers
                                if (Number.isInteger(value)) {
                                    return value;
                                }
                                return null; // Don't show decimal ticks
                            }
                        },
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.1)', // Light horizontal grid lines only
                            lineWidth: 1
                        }
                    },
                    x: {
                        ticks: {
                            maxRotation: 30,
                            autoSkip: false,
                            maxTicksLimit: 10,
                            callback: function(value) {
                                // Truncate long labels
                                let label = this.getLabelForValue(value);
                                if (label.length > 20) {
                                    return label.substring(0, 20) + '...';
                                }
                                return label;
                            }
                        },
                        grid: {
                            display: false // Remove vertical grid lines
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed.y;
                                const hours = (value / 60).toFixed(2);
                                return `${context.dataset.label}: ${value.toFixed(2)} minutes (${hours} hours)`;
                            }
                        }
                    },
                    // Plugin to show value labels on top of bars
                    afterDatasetsDraw: function(chart) {
                        const {ctx, data, chartArea: {top, bottom}, scales: {x, y}} = chart;
                        ctx.save();
                        
                        data.datasets.forEach((dataset, datasetIndex) => {
                            const meta = chart.getDatasetMeta(datasetIndex);
                            
                            meta.data.forEach((bar, index) => {
                                const value = dataset.data[index];
                                
                                // Format the value based on the metric
                                let label = '';
                                if (isOutsideMetric || metricLabel.includes('Time')) {
                                    const hours = (value / 60).toFixed(1);
                                    label = `${value.toFixed(0)} min\n(${hours} h)`;
                                } else {
                                    label = value.toString();
                                }
                                
                                // Position the text above the bar
                                const barCenterX = bar.x;
                                const barTopY = bar.y - 5;
                                
                                ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                                ctx.font = 'bold 11px Arial';
                                ctx.textAlign = 'center';
                                ctx.textBaseline = 'bottom';
                                
                                // Draw the label
                                const lines = label.split('\n');
                                lines.forEach((line, i) => {
                                    ctx.fillText(line, barCenterX, barTopY + (i * 12));
                                });
                            });
                        });
                        
                        ctx.restore();
                    }
                },
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
    
    // Initialize rankings functionality
    function initRankings() {
        // Set default date to yesterday
        setDefaultRankingDate();
        
        // Load initial rankings
        if (rankingDateEl && rankingMetricEl && rankingLimitEl) {
            fetchTopEmployeeRankings(
                rankingDateEl.value, 
                rankingMetricEl.value, 
                rankingLimitEl.value
            );
        }
        
        // Add event listeners for ranking controls
        if (rankingDateEl) {
            rankingDateEl.addEventListener('change', function() {
                if (rankingMetricEl && rankingLimitEl) {
                    fetchTopEmployeeRankings(
                        this.value, 
                        rankingMetricEl.value, 
                        rankingLimitEl.value
                    );
                }
            });
        }
        
        if (rankingMetricEl) {
            rankingMetricEl.addEventListener('change', function() {
                if (rankingDateEl && rankingLimitEl) {
                    fetchTopEmployeeRankings(
                        rankingDateEl.value, 
                        this.value, 
                        rankingLimitEl.value
                    );
                }
            });
        }
        
        if (rankingLimitEl) {
            rankingLimitEl.addEventListener('change', function() {
                if (rankingDateEl && rankingMetricEl) {
                    fetchTopEmployeeRankings(
                        rankingDateEl.value, 
                        rankingMetricEl.value, 
                        this.value
                    );
                }
            });
        }
        
        if (refreshRankingsBtn) {
            refreshRankingsBtn.addEventListener('click', function() {
                if (rankingDateEl && rankingMetricEl && rankingLimitEl) {
                    // Add loading state
                    const originalHTML = refreshRankingsBtn.innerHTML;
                    refreshRankingsBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing';
                    refreshRankingsBtn.disabled = true;
                    
                    fetchTopEmployeeRankings(
                        rankingDateEl.value, 
                        rankingMetricEl.value, 
                        rankingLimitEl.value
                    ).finally(() => {
                        // Restore button state
                        refreshRankingsBtn.innerHTML = originalHTML;
                        refreshRankingsBtn.disabled = false;
                    });
                }
            });
        }
    }
    
    // Initialize rankings when DOM is loaded (if on dashboard)
    if (document.getElementById('dashboard-view') && !document.getElementById('dashboard-view').classList.contains('d-none')) {
        initRankings();
    }
    
    // Top Floor Visitors functionality
    
    // DOM elements for floor visitors
    const floorVisitorDateEl = document.getElementById('floor-visitor-date');
    const floorVisitorLimitEl = document.getElementById('floor-visitor-limit');
    const refreshFloorVisitorsBtn = document.getElementById('refresh-floor-visitors');
    const floorVisitorsListEl = document.getElementById('floor-visitors-list');
    
    // Set default date to yesterday
    function setDefaultFloorVisitorDate() {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        const yesterdayStr = yesterday.toISOString().split('T')[0];
        
        if (floorVisitorDateEl) {
            floorVisitorDateEl.value = yesterdayStr;
        }
    }
    
    // Fetch top floor visitors
    async function fetchTopFloorVisitors(date, limit) {
        if (!checkAuth()) return Promise.resolve();
        
        try {
            // Show loading state
            showFloorVisitorsLoading();
            
            const url = `${API_BASE_URL}/top-floor-visitors?date=${date}&limit=${limit}`;
            const response = await fetch(url);
            const result = await response.json();
            
            if (result.success) {
                renderFloorVisitors(result.data);
            } else {
                showFloorVisitorsError('Failed to load floor visitors: ' + (result.error || 'Unknown error'));
                console.error('Failed to load floor visitors:', result.error);
            }
            return Promise.resolve();
        } catch (error) {
            console.error('Error loading floor visitors:', error);
            showFloorVisitorsError('Error loading floor visitors: ' + error.message);
            return Promise.reject(error);
        }
    }
    
    // Show loading state for floor visitors
    function showFloorVisitorsLoading() {
        if (floorVisitorsListEl) {
            floorVisitorsListEl.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-spinner fa-spin fa-2x text-muted mb-3"></i>
                    <p class="text-muted">Loading floor visitors...</p>
                </div>
            `;
        }
    }
    
    // Show error state for floor visitors
    function showFloorVisitorsError(message) {
        if (floorVisitorsListEl) {
            floorVisitorsListEl.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-exclamation-triangle fa-2x text-warning mb-3"></i>
                    <p class="text-muted">${message}</p>
                </div>
            `;
        }
    }
    
    // Render floor visitors list
    function renderFloorVisitors(visitors) {
        if (!floorVisitorsListEl) return;
        
        if (!visitors || visitors.length === 0) {
            floorVisitorsListEl.innerHTML = `
                <div class="text-center py-5">
                    <i class="fas fa-info-circle fa-2x text-muted mb-3"></i>
                    <p class="text-muted">No floor visitor data available for selected date</p>
                </div>
            `;
            // Hide chart and show message
            const chartContainer = document.getElementById('floor-visitors-chart-container');
            const chartCanvas = document.getElementById('floor-visitors-bar-chart');
            if (chartContainer) chartContainer.style.display = 'none';
            if (floorVisitorsListEl) floorVisitorsListEl.classList.remove('d-none');
            return;
        }
        
        // Prepare data for horizontal bar chart
        const labels = [];
        const data = [];
        
        visitors.forEach((item, index) => {
            const rank = index + 1;
            const employeeId = item.EMPLOYEE_ID || 'N/A';
            const name = item.NAME || 'Unknown';
            const department = item.DEPARTMENT || 'N/A';
            const floorsVisited = item.UNIQUE_FLOORS_VISITED || 0;
            
            // Create a truncated name for better readability on X-axis
            const truncatedName = truncateName(name);
            labels.push(`${rank}. ${employeeId} | ${truncatedName} (${department})`);
            data.push(floorsVisited);
        });
        
        // Destroy existing chart if it exists
        if (window.floorVisitorsChartInstance) {
            window.floorVisitorsChartInstance.destroy();
        }
        
        // Calculate insights for the insight line
        const totalFloors = data.reduce((sum, value) => sum + value, 0);
        const topThreeFloors = data.length >= 3 ? data[0] + data[1] + data[2] : data.reduce((sum, value) => sum + value, 0);
        const topPercentage = totalFloors > 0 ? ((topThreeFloors / totalFloors) * 100).toFixed(0) : 0;
        
        // Update insight text
        const insightElement = document.getElementById('floor-visitors-insight-text');
        if (insightElement) {
            insightElement.textContent = `Most floor visits are concentrated among top 3 employees (${topPercentage}% of total)`;
        }
        
        // Show chart container and hide list
        const chartContainer = document.getElementById('floor-visitors-chart-container');
        const chartCanvas = document.getElementById('floor-visitors-bar-chart');
        if (floorVisitorsListEl) floorVisitorsListEl.classList.add('d-none');
        if (chartContainer) chartContainer.style.display = 'block';
        
        // Set canvas dimensions
        chartCanvas.height = 400; // Fixed height for vertical bar chart
        
        // Create vertical bar chart
        const ctx = chartCanvas.getContext('2d');
        window.floorVisitorsChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Unique Floors Visited',
                    data: data,
                    backgroundColor: data.map((value, index) => {
                        // Highlight the top-ranked bar (first item) with a stronger color
                        if (index === 0) {
                            return 'rgba(13, 110, 253, 1)'; // Stronger blue for rank #1
                        } else {
                            return 'rgba(13, 110, 253, 0.5)'; // Lighter blue for others
                        }
                    }),
                    borderColor: data.map((value, index) => {
                        // Same logic for border
                        if (index === 0) {
                            return 'rgb(13, 110, 253)';
                        } else {
                            return 'rgb(13, 110, 253)';
                        }
                    }),
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'x', // This makes it a vertical bar chart
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Unique Floors Visited'
                        },
                        // Configure ticks to show round values only
                        ticks: {
                            // Ensure clean, round number intervals
                            callback: function(value) {
                                // Only show round numbers
                                if (Number.isInteger(value)) {
                                    return value;
                                }
                                return null; // Don't show decimal ticks
                            }
                        },
                        grid: {
                            display: true,
                            color: 'rgba(0, 0, 0, 0.1)', // Light horizontal grid lines only
                            lineWidth: 1
                        }
                    },
                    x: {
                        ticks: {
                            maxRotation: 30,
                            autoSkip: false,
                            maxTicksLimit: 10,
                            callback: function(value) {
                                // Truncate long labels
                                let label = this.getLabelForValue(value);
                                if (label.length > 20) {
                                    return label.substring(0, 20) + '...';
                                }
                                return label;
                            }
                        },
                        grid: {
                            display: false // Remove vertical grid lines
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed.y;
                                return `${context.dataset.label}: ${value} floor${value !== 1 ? 's' : ''}`;
                            }
                        }
                    },
                    // Plugin to show value labels on top of bars
                    afterDatasetsDraw: function(chart) {
                        const {ctx, data, chartArea: {top, bottom}, scales: {x, y}} = chart;
                        ctx.save();
                        
                        data.datasets.forEach((dataset, datasetIndex) => {
                            const meta = chart.getDatasetMeta(datasetIndex);
                            
                            meta.data.forEach((bar, index) => {
                                const value = dataset.data[index];
                                
                                // Format the value based on the metric
                                const label = `${value} floor${value !== 1 ? 's' : ''}`;
                                
                                // Position the text above the bar
                                const barCenterX = bar.x;
                                const barTopY = bar.y - 5;
                                
                                ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                                ctx.font = 'bold 11px Arial';
                                ctx.textAlign = 'center';
                                ctx.textBaseline = 'bottom';
                                
                                // Draw the label
                                ctx.fillText(label, barCenterX, barTopY);
                            });
                        });
                        
                        ctx.restore();
                    }
                },
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
    
    // Initialize floor visitors functionality
    function initFloorVisitors() {
        // Set default date to yesterday
        setDefaultFloorVisitorDate();
        
        // Load initial floor visitors
        if (floorVisitorDateEl && floorVisitorLimitEl) {
            fetchTopFloorVisitors(
                floorVisitorDateEl.value, 
                floorVisitorLimitEl.value
            );
        }
        
        // Add event listeners for floor visitor controls
        if (floorVisitorDateEl) {
            floorVisitorDateEl.addEventListener('change', function() {
                if (floorVisitorLimitEl) {
                    fetchTopFloorVisitors(
                        this.value, 
                        floorVisitorLimitEl.value
                    );
                }
            });
        }
        
        if (floorVisitorLimitEl) {
            floorVisitorLimitEl.addEventListener('change', function() {
                if (floorVisitorDateEl) {
                    fetchTopFloorVisitors(
                        floorVisitorDateEl.value, 
                        this.value
                    );
                }
            });
        }
        
        if (refreshFloorVisitorsBtn) {
            refreshFloorVisitorsBtn.addEventListener('click', function() {
                if (floorVisitorDateEl && floorVisitorLimitEl) {
                    // Add loading state
                    const originalHTML = refreshFloorVisitorsBtn.innerHTML;
                    refreshFloorVisitorsBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing';
                    refreshFloorVisitorsBtn.disabled = true;
                    
                    fetchTopFloorVisitors(
                        floorVisitorDateEl.value, 
                        floorVisitorLimitEl.value
                    ).finally(() => {
                        // Restore button state
                        refreshFloorVisitorsBtn.innerHTML = originalHTML;
                        refreshFloorVisitorsBtn.disabled = false;
                    });
                }
            });
        }
    }
    
    // Initialize floor visitors when DOM is loaded (if on dashboard)
    if (document.getElementById('dashboard-view') && !document.getElementById('dashboard-view').classList.contains('d-none')) {
        initFloorVisitors();
    }
    
    // Daily Presence Distribution functionality
    
    // DOM elements for presence distribution
    const presenceDateEl = document.getElementById('presence-date');
    const refreshPresenceDistributionBtn = document.getElementById('refresh-presence-distribution');
    const insideProgressEl = document.getElementById('inside-progress');
    const outsideProgressEl = document.getElementById('outside-progress');
    const insideProgressTextEl = document.getElementById('inside-progress-text');
    const outsideProgressTextEl = document.getElementById('outside-progress-text');
    const totalTimeTrackedEl = document.getElementById('total-time-tracked');
    const insightTextEl = document.getElementById('insight-text');
    
    // Set default date to yesterday
    function setDefaultPresenceDate() {
        const yesterday = new Date();
        yesterday.setDate(yesterday.getDate() - 1);
        const yesterdayStr = yesterday.toISOString().split('T')[0];
        
        if (presenceDateEl) {
            presenceDateEl.value = yesterdayStr;
        }
    }
    
    // Fetch daily presence distribution data
    async function fetchDailyPresenceDistribution(date) {
        if (!checkAuth()) return Promise.resolve();
        
        try {
            const url = `${API_BASE_URL}/daily-presence-distribution?date=${date}`;
            const response = await fetch(url);
            const result = await response.json();
            
            if (result.success) {
                renderDailyPresenceDistribution(result.data);
            } else {
                console.error('Failed to load presence distribution:', result.error);
                insightTextEl.innerHTML = '<small class="text-danger">Error loading data: ' + (result.error || 'Unknown error') + '</small>';
            }
            return Promise.resolve();
        } catch (error) {
            console.error('Error loading presence distribution:', error);
            insightTextEl.innerHTML = '<small class="text-danger">Error loading data: ' + error.message + '</small>';
            return Promise.reject(error);
        }
    }
    
    // Render daily presence distribution chart
    function renderDailyPresenceDistribution(data) {
        if (!data) {
            insightTextEl.innerHTML = '<small class="text-muted">No data available for selected date</small>';
            return;
        }
        
        const insideMinutes = data.inside_minutes || 0;
        const outsideMinutes = data.outside_minutes || 0;
        const totalMinutes = data.total_minutes || (insideMinutes + outsideMinutes);
        const insidePercentage = data.inside_percentage !== undefined ? data.inside_percentage : (totalMinutes > 0 ? (insideMinutes / totalMinutes) * 100 : 0);
        const outsidePercentage = data.outside_percentage !== undefined ? data.outside_percentage : (totalMinutes > 0 ? (outsideMinutes / totalMinutes) * 100 : 0);
        

        
        // Update total time tracked
        const totalHours = totalMinutes / 60;
        totalTimeTrackedEl.textContent = `Total Time Tracked: ${totalHours.toFixed(1)} hrs`;
        
        // Generate insight text
        generateInsightText(insideMinutes, outsideMinutes, totalMinutes);
        
        // Create or update the pie chart
        createOrUpdatePieChart(insideMinutes, outsideMinutes, insidePercentage, outsidePercentage);
    }
    
    // Generate insight text based on the data
    function generateInsightText(insideMinutes, outsideMinutes, totalMinutes) {
        if (totalMinutes === 0) {
            insightTextEl.innerHTML = '<small class="text-muted">No movement data recorded for this date</small>';
            return;
        }
        
        // Calculate the ratio of outside to inside time
        const outsideRatio = insideMinutes > 0 ? outsideMinutes / insideMinutes : Infinity;
        
        if (outsideRatio > 1.2) {
            insightTextEl.innerHTML = `<small class="text-warning">↑ Outside time is ${(outsideRatio - 1).toFixed(2) * 100}% higher than inside time</small>`;
        } else if (outsideRatio < 0.8) {
            insightTextEl.innerHTML = `<small class="text-success">↓ Inside time is ${((1 - outsideRatio) * 100).toFixed(2)}% higher than outside time</small>`;
        } else {
            insightTextEl.innerHTML = '<small class="text-info">Balanced time distribution between inside and outside</small>';
        }
    }
    
    // Create or update pie chart for presence distribution
    function createOrUpdatePieChart(insideMinutes, outsideMinutes, insidePercentage, outsidePercentage) {
        const ctx = document.getElementById('presence-distribution-pie-chart');
        if (!ctx) return;
        
        // Destroy existing chart instance if it exists
        if (window.presenceDistributionChartInstance) {
            window.presenceDistributionChartInstance.destroy();
        }
        
        // Create new pie chart
        window.presenceDistributionChartInstance = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: [`Inside (${insideMinutes} min - ${insidePercentage.toFixed(1)}%)`, `Outside (${outsideMinutes} min - ${outsidePercentage.toFixed(1)}%)`],
                datasets: [{
                    data: [insideMinutes, outsideMinutes],
                    backgroundColor: [
                        '#28a745', // Green for Inside
                        '#dc3545'  // Red for Outside
                    ],
                    borderColor: [
                        '#ffffff', // White border for better separation
                        '#ffffff'
                    ],
                    borderWidth: 3,
                    hoverOffset: 8, // Extra space when hovering
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            boxWidth: 15,
                            padding: 15,
                            font: {
                                size: 14,
                                weight: 'bold'
                            },
                            color: '#495057'
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.parsed || 0;
                                const total = insideMinutes + outsideMinutes;
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return `${label}: ${value} min (${percentage}%)`;
                            }
                        },
                        titleFont: {
                            size: 14,
                            weight: 'bold'
                        },
                        bodyFont: {
                            size: 13
                        }
                    }
                },
                cutout: '0%', // Makes it a pie chart (use '50%' for doughnut)
                animation: {
                    animateRotate: true,
                    animateScale: false,
                    duration: 1000,
                    easing: 'easeOutQuart'
                }
            }
        });
    }
    
    // Initialize presence distribution functionality
    function initPresenceDistribution() {
        // Set default date to yesterday
        setDefaultPresenceDate();
        
        // Load initial data
        if (presenceDateEl) {
            fetchDailyPresenceDistribution(presenceDateEl.value);
        }
        
        // Add event listener for date change
        if (presenceDateEl) {
            presenceDateEl.addEventListener('change', function() {
                fetchDailyPresenceDistribution(this.value);
            });
        }
        
        // Add event listener for refresh button
        if (refreshPresenceDistributionBtn) {
            refreshPresenceDistributionBtn.addEventListener('click', function() {
                if (presenceDateEl) {
                    // Add loading state
                    const originalHTML = refreshPresenceDistributionBtn.innerHTML;
                    refreshPresenceDistributionBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing';
                    refreshPresenceDistributionBtn.disabled = true;
                    
                    fetchDailyPresenceDistribution(presenceDateEl.value).finally(() => {
                        // Restore button state
                        refreshPresenceDistributionBtn.innerHTML = originalHTML;
                        refreshPresenceDistributionBtn.disabled = false;
                    });
                }
            });
        }
    }
    
    // Initialize presence distribution when DOM is loaded (if on dashboard)
    if (document.getElementById('dashboard-view') && !document.getElementById('dashboard-view').classList.contains('d-none')) {
        initPresenceDistribution();
    }
    
    // Update sidebar based on admin access - first with cached data (synchronous), then with fresh data (asynchronous)
    // This ensures immediate UI update for returning users while still refreshing data
    const cachedResult = hasAdminAccessSync();
    if (cachedResult !== null) {
        // If we have cached data, update the UI immediately
        const drishtiManagementSection = document.querySelector('[data-bs-target="#drishti-management-submenu"]');
        const drishtiManagementSubmenu = document.getElementById('drishti-management-submenu');
        
        if (drishtiManagementSection && drishtiManagementSubmenu) {
            if (cachedResult) {
                // Show the Drishti Management section
                drishtiManagementSection.style.display = '';
                drishtiManagementSection.classList.remove('d-none', 'hidden-initially');
                // Make sure the parent li element is also visible
                const parentLi = drishtiManagementSection.closest('li');
                if (parentLi) {
                    parentLi.style.display = '';
                    parentLi.classList.remove('d-none', 'hidden-initially');
                }
                // Show the submenu if needed
                drishtiManagementSubmenu.classList.remove('d-none', 'hidden-initially');
            } else {
                // Hide the Drishti Management section
                drishtiManagementSection.style.display = 'none';
                drishtiManagementSection.classList.add('d-none');
                const parentLi = drishtiManagementSection.closest('li');
                if (parentLi) {
                    parentLi.style.display = 'none';
                    parentLi.classList.add('d-none');
                }
                // Also hide the submenu
                drishtiManagementSubmenu.classList.add('d-none');
                drishtiManagementSubmenu.classList.remove('show');
                drishtiManagementSection.setAttribute('aria-expanded', 'false');
            }
        }
    }
    
    // Then update with fresh data asynchronously
    updateSidebarForAdminAccess();
});

// Global logout function that can be used by HTML pages
function globalLogout() {
    localStorage.removeItem('isAdminLoggedIn');
    localStorage.removeItem('currentUser');
    localStorage.removeItem('userAdminAccess');
    window.location.href = 'login.html';
}

// Override logout functionality if logout-link exists
if (document.getElementById('logout-link')) {
    document.getElementById('logout-link').addEventListener('click', function(e) {
        e.preventDefault();
        globalLogout();
    });
}
