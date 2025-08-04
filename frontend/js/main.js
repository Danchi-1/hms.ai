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
                document.querySelectorAll('.auth-tab').forEach(tab => {
                    tab.addEventListener('click', () => this.switchAuthTab(tab.dataset.tab));
                });

                // Form submissions
                document.getElementById('loginForm').addEventListener('submit', (e) => this.handleLogin(e));
                document.getElementById('signupForm').addEventListener('submit', (e) => this.handleSignup(e));

                // Dashboard actions
                document.getElementById('logoutBtn').addEventListener('click', () => this.handleLogout());
                document.getElementById('startCollectionBtn').addEventListener('click', () => this.startDataCollection());
                document.getElementById('stopCollectionBtn').addEventListener('click', () => this.stopDataCollection());
                document.getElementById('runPredictionBtn').addEventListener('click', () => this.runPrediction());
                document.getElementById('trainModelBtn').addEventListener('click', () => this.trainModel());
            }

            switchAuthTab(tabName) {
                document.querySelectorAll('.auth-tab').forEach(tab => {
                    tab.classList.remove('active');
                });
                document.querySelectorAll('.auth-form').forEach(form => {
                    form.classList.remove('active');
                });

                document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
                document.getElementById(`${tabName}Form`).classList.add('active');
            }

            showLoading() {
                document.getElementById('loadingSpinner').classList.add('active');
            }

            hideLoading() {
                document.getElementById('loadingSpinner').classList.remove('active');
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
                    const response = await fetch('/login', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(loginData)
                    });

                    const result = await response.json();

                    if (response.ok) {
                        this.currentUser = result.user;
                        this.showDashboard();
                        this.showNotification('Welcome back!', 'success');
                        this.loadDashboardData();
                    } else {
                        this.showNotification(result.message || 'Login failed', 'error');
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
                    const response = await fetch('/signup', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify(signupData)
                    });

                    const result = await response.json();

                    if (response.ok) {
                        this.currentUser = result.user;
                        this.showDashboard();
                        this.showNotification('Account created successfully!', 'success');
                        this.loadDashboardData();
                    } else {
                        this.showNotification(result.message || 'Signup failed', 'error');
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
                document.getElementById('authPage').style.display = 'flex';
                document.getElementById('dashboardPage').classList.remove('active');
            }

            showDashboard() {
                document.getElementById('authPage').style.display = 'none';
                document.getElementById('dashboardPage').classList.add('active');
                
                if (this.currentUser) {
                    document.getElementById('userName').textContent = this.currentUser.name || this.currentUser.email;
                    document.getElementById('userAvatar').textContent = (this.currentUser.name || this.currentUser.email).charAt(0).toUpperCase();
                }
            }

            checkAuthStatus() {
                // In a real app, you'd check for stored tokens/session
                // For demo purposes, we'll start with the auth page
                this.showAuthPage();
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
            if (authPage.style.display !== 'none') {
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
                spinner.classList.add('active');
            }

            // Function to hide the loading spinner
            function hideLoadingSpinner() {
                const spinner = document.getElementById('loadingSpinner');
                spinner.classList.remove('active');
            }

            // Example usage: Show spinner for 3 seconds, then hide it
            showLoadingSpinner();
            setTimeout(hideLoadingSpinner, 3000);

            // Function to start the pulsing animation on the hero visual
            function startPulsing() {
                const heroImage = document.querySelector('.head-hero-image');
                heroImage.classList.add('pulse');
            }

            // Function to stop the pulsing animation on the hero visual
            function stopPulsing() {
                const heroImage = document.querySelector('.head-hero-image');
                heroImage.classList.remove('pulse');
            }

            // Example usage: Start pulsing animation
            startPulsing();
        });
        document.addEventListener('DOMContentLoaded', function() {
            const signupForm = document.getElementById('signupForm');
            const loginForm = document.getElementById('loginForm');
            const password = document.getElementById('password').value;

            if (signupForm) {
                signupForm.addEventListener('submit', function(event) {
                    event.preventDefault();
                    const confirmPassword = document.getElementById('confirm_password').value;
                    if (password != confirmPassword) {
                        alert('passwords do not match');
                        return false;                        
                    }
                    // Redirect to dashboard.html after signup
                    window.location.href = 'dashboard.html';
                });
            }

            if (loginForm) {
                loginForm.addEventListener('submit', function(event) {
                    event.preventDefault();
                        // Redirect to dashboard.html after login
                        window.location.href = 'dashboard.html';
                });
            }
        });

        document.addEventListener('DOMContentLoaded', function() {
            const dashboardBtn = document.getElementById('dashboard-btn-home');
        });