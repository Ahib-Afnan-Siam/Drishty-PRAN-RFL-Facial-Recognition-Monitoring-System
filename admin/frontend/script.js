/*
 * Admin Dashboard JavaScript
 */

// API base URL
const API_BASE_URL = 'http://localhost:5001/api';

// Global variables to store current data and state
let currentSummaryData = [];
let filteredSummaryData = [];
let currentSort = { column: null, direction: 'asc' };

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

const camerasTableBody = document.querySelector('#cameras-table tbody');
const summaryTableBody = document.querySelector('#summary-table tbody');

// Search element for employee summary
const summarySearchEl = document.getElementById('summary-search');

// View elements
const dashboardView = document.getElementById('dashboard-view');
const camerasView = document.getElementById('cameras-view');
const summaryView = document.getElementById('summary-view');
const addCameraView = document.getElementById('add-camera-view');
const updateCameraStatusView = document.getElementById('update-camera-status-view');

// Sidebar navigation links
const dashboardLink = document.getElementById('dashboard-link');
const reportsDropdown = document.getElementById('reports-dropdown');
const camerasLink = document.getElementById('cameras-link');
const summaryLink = document.getElementById('summary-link');
const faceRecognitionLink = document.getElementById('face-recognition-link');
const addCameraLink = document.getElementById('add-camera-link');
const updateCameraStatusLink = document.getElementById('update-camera-status-link');
const cameraInfoDropdown = document.getElementById('camera-info-dropdown');

// Report links (newly added)
const reportLinks = document.querySelectorAll('.report-link');
const cameraInfoLinks = document.querySelectorAll('.camera-info-link');

// Set default dates (last 7 days)
function setDefaultDates() {
    const today = new Date();
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);
    
    // Format as YYYY-MM-DD
    const todayStr = today.toISOString().split('T')[0];
    const lastWeekStr = lastWeek.toISOString().split('T')[0];
    
    toDateEl.value = todayStr;
    fromDateEl.value = lastWeekStr;
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

// Check if user is authenticated
function checkAuth() {
    const isLoggedIn = localStorage.getItem('isAdminLoggedIn');
    if (!isLoggedIn) {
        window.location.href = 'login.html';
        return false;
    }
    return true;
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
            
            // Apply any existing search filter
            applySearchFilter();
            
            // Render the data
            renderEmployeeSummary(filteredSummaryData);
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

// Sort data by column
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

// Show a specific view and hide others
function showView(viewName) {
    if (!checkAuth()) return;
    
    // Hide all views
    dashboardView.classList.add('d-none');
    camerasView.classList.add('d-none');
    summaryView.classList.add('d-none');
    addCameraView.classList.add('d-none');
    updateCameraStatusView.classList.add('d-none');
    
    // Remove active class from all sidebar links
    dashboardLink.classList.remove('active');
    reportsDropdown.classList.remove('active');
    camerasLink.classList.remove('active');
    summaryLink.classList.remove('active');
    faceRecognitionLink.classList.remove('active');
    document.getElementById('add-camera-link').classList.remove('active');
    document.getElementById('update-camera-status-link').classList.remove('active');
    document.getElementById('camera-info-dropdown').classList.remove('active');
    document.getElementById('logout-link').classList.remove('active');
    
    // Show the selected view
    if (viewName === 'dashboard') {
        dashboardView.classList.remove('d-none');
        dashboardLink.classList.add('active');
    } else if (viewName === 'cameras') {
        camerasView.classList.remove('d-none');
        camerasLink.classList.add('active');
        // Load camera data if not already loaded
        if (camerasTableBody.innerHTML.trim() === '') {
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
        summaryView.classList.remove('d-none');
        summaryLink.classList.add('active');
        // Load summary data if not already loaded
        if (summaryTableBody.innerHTML.trim() === '' || summaryTableBody.innerHTML.includes('No employee data found')) {
            // Add loading state
            const summaryCard = document.querySelector('#summary-view .card');
            if (summaryCard) {
                summaryCard.classList.add('btn-loading');
            }
            
            fetchEmployeeSummary(fromDateEl.value, toDateEl.value).finally(() => {
                // Remove loading state
                if (summaryCard) {
                    summaryCard.classList.remove('btn-loading');
                }
            });
        }
    } else if (viewName === 'face-recognition') {
        // For face recognition, we just show the active state on the link
        // The actual redirection happens in the click handler
        faceRecognitionLink.classList.add('active');
    } else if (viewName === 'add-camera') {
        addCameraView.classList.remove('d-none');
        document.getElementById('add-camera-link').classList.add('active');
        // Redirect to the dedicated add camera page
        window.location.href = 'add_camera.html';
    } else if (viewName === 'update-camera-status') {
        updateCameraStatusView.classList.remove('d-none');
        document.getElementById('update-camera-status-link').classList.add('active');
        // Redirect to the dedicated update camera status page
        window.location.href = 'update_camera_status.html';
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
    // Add loading state to dashboard stats
    const statCards = document.querySelectorAll('#dashboard-stats .card');
    statCards.forEach(card => {
        card.classList.add('btn-loading');
    });
    
    fetchDashboardStats().finally(() => {
        // Remove loading state
        statCards.forEach(card => {
            card.classList.remove('btn-loading');
        });
    });
    
    // Sidebar navigation
    dashboardLink.addEventListener('click', function(e) {
        e.preventDefault();
        showView('dashboard');
    });
    
    // Reports dropdown toggle - removed manual handling since we're using Bootstrap's collapse
    
    // Report links (both camera registry and employee summary)
    reportLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const viewName = this.id.replace('-link', '');
            showView(viewName);
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
    
    // Camera Info dropdown click handler
    cameraInfoDropdown.addEventListener('click', function(e) {
        // Just toggle the dropdown, don't change the active state of other items
        // The active state should remain on the currently selected item
        e.stopPropagation();
    });
    
    // Camera Info links (both add camera and update camera status)
    cameraInfoLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            const viewName = this.id.replace('-link', '');
            showView(viewName);
        });
    })
    
    // Refresh buttons
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
    
    refreshSummaryBtn.addEventListener('click', function() {
        // Add loading state
        const originalHTML = refreshSummaryBtn.innerHTML;
        refreshSummaryBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        refreshSummaryBtn.classList.add('btn-loading');
        
        // Fetch data
        fetchEmployeeSummary(fromDateEl.value, toDateEl.value).finally(() => {
            // Remove loading state
            refreshSummaryBtn.innerHTML = originalHTML;
            refreshSummaryBtn.classList.remove('btn-loading');
        });
    });
    
    // Apply filter button
    applyFilterBtn.addEventListener('click', () => {
        if (fromDateEl.value && toDateEl.value) {
            // Add loading state
            const originalHTML = applyFilterBtn.innerHTML;
            applyFilterBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Applying...';
            applyFilterBtn.classList.add('btn-loading');
            
            // Fetch data
            fetchEmployeeSummary(fromDateEl.value, toDateEl.value).finally(() => {
                // Remove loading state
                applyFilterBtn.innerHTML = originalHTML;
                applyFilterBtn.classList.remove('btn-loading');
            });
        } else {
            showAlert('Please select both from and to dates', 'warning');
        }
    });
    
    // Search input event listener
    summarySearchEl.addEventListener('input', () => {
        applySearchFilter();
        renderEmployeeSummary(filteredSummaryData);
    });
    
    // Sort option event listeners
    const sortOptions = document.querySelectorAll('.sort-option');
    sortOptions.forEach(option => {
        option.addEventListener('click', (e) => {
            e.preventDefault();
            const column = e.target.getAttribute('data-sort');
            const direction = e.target.getAttribute('data-dir');
            
            currentSort = { column, direction };
            sortData(column, direction);
            renderEmployeeSummary(filteredSummaryData);
            
            // Update button text to show current sort
            const sortButton = document.querySelector('.dropdown-toggle');
            sortButton.innerHTML = `<i class="fas fa-sort"></i> Sorted by ${e.target.textContent}`;
        });
    });
    
    // User Management dropdown click handler
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
            // Redirect to user management page
            window.location.href = 'user_management.html';
        });
    });
    
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
    
    // Check for hash in URL to determine which view to show
    const hash = window.location.hash;
    if (hash === '#cameras') {
        showView('cameras');
    } else {
        // Show dashboard view by default
        showView('dashboard');
    }
});