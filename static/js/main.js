const getApiBaseUrl = () => {
    // Check if we are in a production environment (Vercel, etc.)
    const hostname = window.location.hostname;
    if (hostname.includes('vercel.app') || hostname.includes('github.io')) {
        return 'https://hmsai.onrender.com';
    }
    // Default to relative path for localhost or same-origin deployment
    return '';
};

const API_BASE = getApiBaseUrl();
// Vercel Cache Buster: v3.1

class HMSApp {
    constructor() {
        this.currentUser = null;
        this.isCollecting = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkAuthStatus();
    }

    setupEventListeners() {
        // Auth tab switching
        const authTabs = document.querySelectorAll('.auth-tab');
        if (authTabs.length > 0) {
            authTabs.forEach(tab => {
                tab.addEventListener('click', () => this.switchAuthTab(tab.dataset.tab));
            });
        }

        // Form submissions
        const loginForm = document.getElementById('loginForm');
        if (loginForm) loginForm.addEventListener('submit', (e) => this.handleLogin(e));

        const signupForm = document.getElementById('signupForm');
        if (signupForm) signupForm.addEventListener('submit', (e) => this.handleSignup(e));

        // Dashboard actions
        const logoutBtn = document.getElementById('logoutBtn');
        if (logoutBtn) logoutBtn.addEventListener('click', () => this.handleLogout());

        const startBtn = document.getElementById('startCollectionBtn');
        if (startBtn) startBtn.addEventListener('click', () => this.startDataCollection());

        const stopBtn = document.getElementById('stopCollectionBtn');
        if (stopBtn) stopBtn.addEventListener('click', () => this.stopDataCollection());

        const predictBtn = document.getElementById('runPredictionBtn');
        if (predictBtn) predictBtn.addEventListener('click', () => this.runPrediction());

        const trainBtn = document.getElementById('trainModelBtn');
        if (trainBtn) trainBtn.addEventListener('click', () => this.trainModel());

        // Mobile Menu Toggle
        const mobileMenuBtn = document.getElementById('mobileMenuBtn');
        const navLinks = document.getElementById('navLinks');

        if (mobileMenuBtn && navLinks) {
            mobileMenuBtn.addEventListener('click', () => {
                navLinks.classList.toggle('active');

                // Toggle icon
                const icon = mobileMenuBtn.querySelector('i');
                if (navLinks.classList.contains('active')) {
                    icon.classList.remove('fa-bars');
                    icon.classList.add('fa-times');
                } else {
                    icon.classList.remove('fa-times');
                    icon.classList.add('fa-bars');
                }
            });

            // Close menu when clicking outside
            document.addEventListener('click', (e) => {
                if (!navLinks.contains(e.target) && !mobileMenuBtn.contains(e.target) && navLinks.classList.contains('active')) {
                    navLinks.classList.remove('active');
                    const icon = mobileMenuBtn.querySelector('i');
                    icon.classList.remove('fa-times');
                    icon.classList.add('fa-bars');
                }
            });
        }
    }




    switchAuthTab(tabName) {
        if (!tabName) return;

        const tabs = document.querySelectorAll('.auth-tab');
        const forms = document.querySelectorAll('.auth-form');

        if (tabs.length === 0 || forms.length === 0) return;

        tabs.forEach(tab => {
            tab.classList.remove('active');
        });
        forms.forEach(form => {
            form.classList.remove('active');
        });

        const targetTab = document.querySelector(`[data-tab="${tabName}"]`);
        const targetForm = document.getElementById(`${tabName}Form`);

        if (targetTab) targetTab.classList.add('active');
        if (targetForm) targetForm.classList.add('active');
    }

    showLoading() {
        document.getElementById('loadingSpinner').classList.add('active');
    }

    hideLoading() {
        const spinner = document.getElementById('loadingSpinner');
        if (spinner) spinner.classList.remove('active');
        
        // Also reset auth buttons if they are stuck in loading state (e.g. on error)
        const loginBtn = document.getElementById('loginBtn');
        const signupBtn = document.getElementById('signupBtn');
        if (loginBtn) loginBtn.classList.remove('loading');
        if (signupBtn) signupBtn.classList.remove('loading');
    }

    showNotification(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        document.body.appendChild(notification);

        setTimeout(() => {
            notification.classList.add('show');
        }, 100);

        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }

    async handleLogin(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const loginData = {
            email: formData.get('email'),
            password: formData.get('password')
        };

        this.showLoading();

        try {
            const response = await fetch(`${API_BASE}/api/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(loginData)
            });

            const result = await response.json();

            if (response.ok) {
                // For Vercel/Static deployment, we can't rely on server redirect logic implicitly if serving index.html
                // But /dashboard is rewritten to /templates/dashboard.html in vercel.json
                window.location.href = '/dashboard';
            } else {
                this.showNotification(result.error || result.message || 'Login failed', 'error');
            }
        } catch (error) {
            this.showNotification('Connection error. Please try again.', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async handleSignup(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const signupData = {
            name: formData.get('name'),
            email: formData.get('email'),
            password: formData.get('password'),
            confirmPassword: formData.get('confirmPassword')
        };

        if (signupData.password !== signupData.confirmPassword) {
            this.showNotification('Passwords do not match', 'error');
            return;
        }

        this.showLoading();

        try {
            // Map form data to API expectations (name -> username)
            const apiData = {
                username: signupData.name,
                email: signupData.email,
                password: signupData.password
            };

            const response = await fetch(`${API_BASE}/api/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(apiData)
            });

            const result = await response.json();

            if (response.ok) {
                window.location.href = '/dashboard';
            } else {
                this.showNotification(result.error || result.message || 'Signup failed', 'error');
            }
        } catch (error) {
            this.showNotification('Connection error. Please try again.', 'error');
        } finally {
            this.hideLoading();
        }
    }

    handleLogout() {
        this.currentUser = null;
        this.showAuthPage();
        this.showNotification('Logged out successfully', 'success');
    }

    showAuthPage() {
        const authPage = document.getElementById('authPage');
        const dashboardPage = document.getElementById('dashboardPage');
        if (authPage && dashboardPage) {
            authPage.style.display = 'flex';
            dashboardPage.classList.remove('active');
        } else {
            // Fallback for non-SPA: redirect to login
            window.location.href = '/login';
        }
    }

    showDashboard() {
        const authPage = document.getElementById('authPage');
        const dashboardPage = document.getElementById('dashboardPage');

        if (authPage && dashboardPage) {
            authPage.style.display = 'none';
            dashboardPage.classList.add('active');

            if (this.currentUser) {
                const nameEl = document.getElementById('userName');
                const avatarEl = document.getElementById('userAvatar');
                if (nameEl) nameEl.textContent = this.currentUser.name || this.currentUser.email;
                if (avatarEl) avatarEl.textContent = (this.currentUser.name || this.currentUser.email).charAt(0).toUpperCase();
            }
        }
    }

    checkAuthStatus() {
        // Only run SPA auth check if we are in the SPA environment
        const authPage = document.getElementById('authPage');
        if (authPage) {
            this.showAuthPage();
        }
    }

    async loadDashboardData() {
        try {
            const response = await fetch('/dashboard-data');
            const data = await response.json();

            if (response.ok) {
                this.updateHealthMetrics(data);
            }
        } catch (error) {
            console.error('Error loading dashboard data:', error);
        }
    }

    updateHealthMetrics(data) {
        const heartRateEl = document.getElementById('heartRate');
        const bloodOxygenEl = document.getElementById('bloodOxygen');
        const healthStatusEl = document.getElementById('healthStatus');

        if (data.heartRate) {
            heartRateEl.textContent = data.heartRate;
            heartRateEl.classList.add('pulse');
        }

        if (data.bloodOxygen) {
            bloodOxygenEl.textContent = data.bloodOxygen;
        }

        if (data.status) {
            healthStatusEl.textContent = data.status;
            healthStatusEl.className = `status-indicator status-${data.status.toLowerCase()}`;
        }

        // Trigger AI analysis with the new metrics
        if (data.heartRate && data.bloodOxygen) {
            this.fetchAIAdvice({
                metrics: {
                    heart_rate: data.heartRate,
                    spo2: data.bloodOxygen,
                    timestamp: new Date().toISOString()
                },
                risk_level: data.status || 'Unknown'
            });
        }
    }

    async fetchAIAdvice(contextData) {
        const recommendationList = document.getElementById('recommendationList');
        const summaryEl = document.getElementById('healthScoreDescription');
        const escalationEl = document.getElementById('escalationNotice');

        // Show loading state if not already loading
        if (recommendationList.children.length === 0 || !recommendationList.querySelector('.loading-recommendation')) {
            recommendationList.innerHTML = '<li class="loading-recommendation">🤖 AI is analyzing your latest vitals...</li>';
        }

        try {
            const response = await fetch(`${API_BASE}/api/ai/health-advice`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(contextData)
            });

            const result = await response.json();

            if (response.ok) {
                // Update Summary
                if (result.summary) {
                    summaryEl.textContent = result.summary;
                }

                // Update Recommendations
                recommendationList.innerHTML = '';
                if (result.recommended_actions && result.recommended_actions.length > 0) {
                    result.recommended_actions.forEach(action => {
                        const li = document.createElement('li');
                        li.textContent = action;
                        recommendationList.appendChild(li);
                    });
                } else {
                    const li = document.createElement('li');
                    li.textContent = "No specific actions recommended at this time.";
                    recommendationList.appendChild(li);
                }

                // Handle Escalation
                if (result.escalation_notice) {
                    escalationEl.textContent = result.escalation_notice;
                    escalationEl.style.display = 'flex';
                } else {
                    escalationEl.style.display = 'none';
                }

                // Observations could go to score breakdown (optional enhancement)
                const breakdownEl = document.getElementById('scoreBreakdown');
                if (breakdownEl && result.observations) {
                    breakdownEl.innerHTML = result.observations.map(obs => `<div class="breakdown-item">• ${obs}</div>`).join('');
                }

            } else {
                console.warn('AI Advice failed:', result);
                recommendationList.innerHTML = '<li>⚠️ automated analysis temporarily unavailable.</li>';
            }
        } catch (error) {
            console.error('AI Connection error:', error);
            recommendationList.innerHTML = '<li>⚠️ Connection error retrieving analysis.</li>';
        }
    }

    async startDataCollection() {
        this.showLoading();

        try {
            const response = await fetch('/collect-data');
            const result = await response.json();

            if (response.ok) {
                this.isCollecting = true;
                document.getElementById('startCollectionBtn').disabled = true;
                document.getElementById('stopCollectionBtn').disabled = false;
                this.showNotification('Data collection started', 'success');
                this.startDataRefresh();
            } else {
                this.showNotification(result.message || 'Failed to start collection', 'error');
            }
        } catch (error) {
            this.showNotification('Connection error', 'error');
        } finally {
            this.hideLoading();
        }
    }

    stopDataCollection() {
        this.isCollecting = false;
        document.getElementById('startCollectionBtn').disabled = false;
        document.getElementById('stopCollectionBtn').disabled = true;
        this.showNotification('Data collection stopped', 'warning');
        clearInterval(this.dataRefreshInterval);
    }

    startDataRefresh() {
        // Refresh data every 5 seconds when collecting
        this.dataRefreshInterval = setInterval(() => {
            if (this.isCollecting) {
                this.loadDashboardData();
            }
        }, 5000);
    }

    async runPrediction() {
        this.showLoading();

        try {
            const response = await fetch('/predict');
            const result = await response.json();

            if (response.ok) {
                this.updateHealthMetrics(result);
                this.showNotification('Prediction completed successfully', 'success');
            } else {
                this.showNotification(result.message || 'Prediction failed', 'error');
            }
        } catch (error) {
            this.showNotification('Connection error', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async trainModel() {
        this.showLoading();

        try {
            const response = await fetch('/train-model');
            const result = await response.json();

            if (response.ok) {
                this.showNotification('Model training completed successfully', 'success');
            } else {
                this.showNotification(result.message || 'Training failed', 'error');
            }
        } catch (error) {
            this.showNotification('Connection error', 'error');
        } finally {
            this.hideLoading();
        }
    }

    // Simulate real-time data updates for demo
    simulateRealTimeData() {
        if (this.isCollecting) {
            const heartRate = Math.floor(Math.random() * 40) + 60; // 60-100 BPM
            const bloodOxygen = Math.floor(Math.random() * 5) + 95; // 95-100%
            const statuses = ['normal', 'warning', 'critical'];
            const status = statuses[Math.floor(Math.random() * statuses.length)];

            this.updateHealthMetrics({
                heartRate,
                bloodOxygen,
                status
            });
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.hmsApp = new HMSApp();

    // Add some demo data simulation
    setInterval(() => {
        if (window.hmsApp.isCollecting) {
            window.hmsApp.simulateRealTimeData();
        }
    }, 3000);
});

// Add some interactive animations
document.addEventListener('mousemove', (e) => {
    const authPage = document.getElementById('authPage');
    if (authPage && authPage.style.display !== 'none') {
        const x = e.clientX / window.innerWidth;
        const y = e.clientY / window.innerHeight;

        authPage.style.background = `
                    radial-gradient(circle at ${x * 100}% ${y * 100}%, 
                    rgba(102, 126, 234, 0.1) 0%, 
                    rgba(15, 20, 25, 0.8) 50%)
                `;
    }
});

document.addEventListener('DOMContentLoaded', () => {
    // Function to show the loading spinner
    function showLoadingSpinner() {
        const spinner = document.getElementById('loadingSpinner');
        if (spinner) spinner.classList.add('active');
    }

    // Function to hide the loading spinner
    function hideLoadingSpinner() {
        const spinner = document.getElementById('loadingSpinner');
        if (spinner) spinner.classList.remove('active');
    }

    // Example usage: Show spinner for 3 seconds, then hide it
    // Only run this if we are on a page with a spinner initial state usually
    // or just checking if spinner exists is enough.
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        showLoadingSpinner();
        setTimeout(hideLoadingSpinner, 3000);
    }

    // Function to start the pulsing animation on the hero visual
    function startPulsing() {
        const heroImage = document.querySelector('.head-hero-image');
        if (heroImage) heroImage.classList.add('pulse');
    }

    // Function to stop the pulsing animation on the hero visual
    function stopPulsing() {
        const heroImage = document.querySelector('.head-hero-image');
        if (heroImage) heroImage.classList.remove('pulse');
    }

    // Example usage: Start pulsing animation
    startPulsing();
});