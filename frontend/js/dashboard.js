// Dashboard.js - Enhanced with real API integration
class DashboardManager {
    constructor() {
        this.userId = this.getUserId();
        this.refreshInterval = null;
        this.charts = {};
        this.isLoading = false;
        this.lastUpdate = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadUserProfile();
        this.loadDashboardData();
        this.startAutoRefresh();
    }

    getUserId() {
        // Extract user ID from session or URL params
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get('user_id') || this.getSessionUserId() || 1;
    }

    getSessionUserId() {
        // Try to get user ID from session storage or local user data
        const userData = sessionStorage.getItem('userData');
        if (userData) {
            try {
                return JSON.parse(userData).id;
            } catch (e) {
                console.error('Error parsing user data:', e);
            }
        }
        return null;
    }

    setupEventListeners() {
        // Refresh button
        document.getElementById('refreshBtn')?.addEventListener('click', () => {
            this.loadDashboardData(true);
        });

        // Logout button
        document.getElementById('logoutBtn')?.addEventListener('click', () => {
            this.logout();
        });

        // Retry button
        document.getElementById('retryBtn')?.addEventListener('click', () => {
            this.loadDashboardData(true);
        });

        // Quick action buttons
        document.getElementById('startWorkout')?.addEventListener('click', () => {
            this.startWorkout();
        });

        document.getElementById('logMedicine')?.addEventListener('click', () => {
            this.logMedicine();
        });

        document.getElementById('emergencyContact')?.addEventListener('click', () => {
            this.emergencyContact();
        });

        document.getElementById('exportData')?.addEventListener('click', () => {
            this.exportData();
        });

        document.getElementById('scanDevicesBtn')?.addEventListener('click', () => {
            this.scanForDevices();
        });

        // Window focus event to refresh data
        window.addEventListener('focus', () => {
            if (this.lastUpdate && Date.now() - this.lastUpdate > 300000) { // 5 minutes
                this.loadDashboardData();
            }
        });
    }

    async loadUserProfile() {
        try {
            const response = await fetch('/api/user/profile', {
                credentials: 'include'
            });
            
            if (response.ok) {
                const userData = await response.json();
                this.updateUserProfile(userData);
            } else {
                // Fallback to session data or default
                this.updateUserProfile({
                    name: 'User',
                    email: 'user@example.com',
                    initials: 'U'
                });
            }
        } catch (error) {
            console.error('Failed to load user profile:', error);
            this.updateUserProfile({
                name: 'Health User',
                email: 'user@hms.ai',
                initials: 'HU'
            });
        }
    }

    updateUserProfile(userData) {
        const userName = document.getElementById('userName');
        const userEmail = document.getElementById('userEmail');
        const userAvatar = document.getElementById('userAvatar');
        const welcomeUserName = document.getElementById('welcomeUserName');

        if (userName) userName.textContent = userData.name || 'User';
        if (userEmail) userEmail.textContent = userData.email || '';
        if (welcomeUserName) welcomeUserName.textContent = (userData.name || 'User').split(' ')[0];
        
        if (userAvatar) {
            userAvatar.textContent = userData.initials || userData.name?.charAt(0).toUpperCase() || 'U';
            userAvatar.style.background = this.generateAvatarColor(userData.name || userData.email || 'user');
        }
    }

    generateAvatarColor(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            hash = str.charCodeAt(i) + ((hash << 5) - hash);
        }
        const hue = hash % 360;
        return `linear-gradient(135deg, hsl(${hue}, 60%, 50%) 0%, hsl(${hue + 30}, 70%, 45%) 100%)`;
    }

    async loadDashboardData(forceRefresh = false) {
        if (this.isLoading && !forceRefresh) return;
        
        this.isLoading = true;
        this.showLoading(true);
        this.hideError();

        try {
            const response = await fetch(`/api/dashboard/${this.userId}`, {
                credentials: 'include',
                cache: forceRefresh ? 'no-cache' : 'default'
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            this.updateDashboard(data);
            this.lastUpdate = Date.now();
            this.updateLastUpdatedTime();
            
        } catch (error) {
            console.error('Failed to load dashboard data:', error);
            this.showError(error.message);
            this.loadFallbackData(); // Show some demo data instead of blank dashboard
        } finally {
            this.isLoading = false;
            this.showLoading(false);
        }
    }

    updateDashboard(data) {
        this.updateHealthMetrics(data.summary);
        this.updateAIAnalysis(data);
        this.updateSleepData(data.summary.sleep, data.raw_data.sleep);
        this.updateVitalSigns(data.raw_data);
        this.updateDeviceStatus(data);
        this.updateConnectionStatus(true);
        
        // Update welcome message
        const welcomeMessage = document.getElementById('welcomeMessage');
        if (welcomeMessage) {
            const timeOfDay = this.getTimeOfDay();
            welcomeMessage.textContent = `Here's your health overview for this ${timeOfDay}`;
        }
    }

    updateHealthMetrics(summary) {
        // Heart Rate
        const heartRateEl = document.getElementById('heartRate');
        const heartRateStatus = document.getElementById('heartRateStatus');
        const heartRateTrend = document.getElementById('heartRateTrend');
        
        if (summary.heart_rate && summary.heart_rate.avg_heart_rate) {
            const avgHR = Math.round(summary.heart_rate.avg_heart_rate);
            if (heartRateEl) heartRateEl.textContent = avgHR;
            if (heartRateStatus) {
                heartRateStatus.textContent = this.getHeartRateStatus(avgHR);
                heartRateStatus.className = `status-indicator ${this.getHeartRateStatusClass(avgHR)}`;
            }
            if (heartRateTrend) {
                heartRateTrend.innerHTML = this.generateTrendIndicator('heart_rate', avgHR);
            }
        }

        // Steps
        const stepsEl = document.getElementById('steps');
        const stepsStatus = document.getElementById('stepsStatus');
        const stepsProgress = document.getElementById('stepsProgress');
        
        if (summary.activity && summary.activity.avg_steps) {
            const steps = Math.round(summary.activity.avg_steps);
            if (stepsEl) stepsEl.textContent = steps.toLocaleString();
            
            const goal = 10000;
            const percentage = Math.min((steps / goal) * 100, 100);
            
            if (stepsProgress) {
                stepsProgress.style.width = `${percentage}%`;
                stepsProgress.style.background = percentage >= 100 ? 
                    'linear-gradient(90deg, #48bb78, #38a169)' : 
                    'linear-gradient(90deg, #ed8936, #dd6b20)';
            }
            
            if (stepsStatus) {
                stepsStatus.textContent = steps >= goal ? 'Goal Reached!' : `${Math.round(percentage)}% of goal`;
                stepsStatus.className = `status-indicator ${steps >= goal ? 'status-excellent' : 'status-normal'}`;
            }
        }

        // Calories
        const caloriesEl = document.getElementById('calories');
        const caloriesStatus = document.getElementById('caloriesStatus');
        const caloriesTrend = document.getElementById('caloriesTrend');
        
        if (summary.activity && summary.activity.avg_calories) {
            const calories = Math.round(summary.activity.avg_calories);
            if (caloriesEl) caloriesEl.textContent = calories.toLocaleString();
            if (caloriesStatus) {
                caloriesStatus.textContent = calories >= 2000 ? 'Great burn!' : 'Keep going!';
                caloriesStatus.className = `status-indicator ${calories >= 2000 ? 'status-excellent' : 'status-normal'}`;
            }
            if (caloriesTrend) {
                caloriesTrend.innerHTML = this.generateTrendIndicator('calories', calories);
            }
        }
    }

    updateAIAnalysis(data) {
        // Calculate health score based on available data
        const healthScore = this.calculateHealthScore(data.summary);
        const healthScoreEl = document.getElementById('healthScore');
        const healthScoreCircle = document.getElementById('healthScoreCircle');
        const healthScoreDescription = document.getElementById('healthScoreDescription');
        
        if (healthScoreEl) healthScoreEl.textContent = healthScore;
        if (healthScoreCircle) {
            healthScoreCircle.style.background = `conic-gradient(#48bb78 0deg ${healthScore * 3.6}deg, #e2e8f0 ${healthScore * 3.6}deg 360deg)`;
        }
        
        if (healthScoreDescription) {
            healthScoreDescription.textContent = this.generateHealthScoreDescription(healthScore, data.summary);
        }

        // Generate AI recommendations
        const recommendations = this.generateRecommendations(data.summary);
        const recommendationList = document.getElementById('recommendationList');
        if (recommendationList && recommendations.length > 0) {
            recommendationList.innerHTML = recommendations.map(rec => 
                `<li><span class="rec-icon">${rec.icon}</span> ${rec.text}</li>`
            ).join('');
        }

        // Update confidence score
        const confidenceScore = document.getElementById('confidenceScore');
        if (confidenceScore) {
            const confidence = this.calculateConfidence(data.summary);
            confidenceScore.textContent = confidence;
        }
    }

    updateSleepData(sleepSummary, sleepRawData) {
        const sleepHours = document.getElementById('sleepHours');
        const sleepQuality = document.getElementById('sleepQuality');
        const sleepHoursStatus = document.getElementById('sleepHoursStatus');
        const sleepQualityStatus = document.getElementById('sleepQualityStatus');

        if (sleepSummary && sleepSummary.avg_sleep_duration) {
            const hours = (sleepSummary.avg_sleep_duration / 60).toFixed(1);
            if (sleepHours) sleepHours.textContent = hours;
            if (sleepHoursStatus) {
                sleepHoursStatus.textContent = this.getSleepHoursStatus(hours);
                sleepHoursStatus.className = `status-indicator ${this.getSleepHoursStatusClass(hours)}`;
            }
        }

        if (sleepSummary && sleepSummary.avg_sleep_efficiency) {
            const efficiency = Math.round(sleepSummary.avg_sleep_efficiency);
            if (sleepQuality) sleepQuality.textContent = `${efficiency}%`;
            if (sleepQualityStatus) {
                sleepQualityStatus.textContent = this.getSleepEfficiencyStatus(efficiency);
                sleepQualityStatus.className = `status-indicator ${this.getSleepEfficiencyStatusClass(efficiency)}`;
            }
        }

        // Update sleep chart
        this.updateSleepChart(sleepRawData);
    }

    updateSleepChart(sleepData) {
        const canvas = document.getElementById('sleepChart');
        if (!canvas || !sleepData || sleepData.length === 0) return;

        const ctx = canvas.getContext('2d');
        
        // Destroy existing chart
        if (this.charts.sleep) {
            this.charts.sleep.destroy();
        }

        const last7Days = sleepData.slice(-7);
        const labels = last7Days.map(day => {
            const date = new Date(day.date);
            return date.toLocaleDateString('en-US', { weekday: 'short' });
        });
        
        const sleepHours = last7Days.map(day => (day.total_minutes_asleep / 60).toFixed(1));
        const efficiency = last7Days.map(day => day.sleep_efficiency || 0);

        this.charts.sleep = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Hours Slept',
                    data: sleepHours,
                    borderColor: '#4c51bf',
                    backgroundColor: 'rgba(76, 81, 191, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y'
                }, {
                    label: 'Sleep Efficiency (%)',
                    data: efficiency,
                    borderColor: '#6b46c1',
                    backgroundColor: 'rgba(107, 70, 193, 0.1)',
                    tension: 0.4,
                    yAxisID: 'y1'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Hours'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Efficiency %'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                }
            }
        });
    }

    updateVitalSigns(rawData) {
        // For now, show simulated vital signs since they're not in the current data structure
        // This would be updated when actual vital signs data is available
        
        const bloodPressure = document.getElementById('bloodPressure');
        const bloodOxygen = document.getElementById('bloodOxygen');
        const temperature = document.getElementById('temperature');
        
        // Simulate realistic vital signs based on heart rate if available
        if (rawData.heart_rate && rawData.heart_rate.length > 0) {
            const latestHR = rawData.heart_rate[rawData.heart_rate.length - 1].heart_rate;
            
            // Simulate blood pressure based on heart rate
            const systolic = Math.round(120 + (latestHR - 70) * 0.5);
            const diastolic = Math.round(80 + (latestHR - 70) * 0.3);
            
            if (bloodPressure) bloodPressure.textContent = `${systolic}/${diastolic} mmHg`;
            
            // Simulate other vitals
            if (bloodOxygen) bloodOxygen.textContent = `${Math.round(97 + Math.random() * 2)}%`;
            if (temperature) temperature.textContent = `${(98.6 + (Math.random() - 0.5) * 1).toFixed(1)}°F`;
            
            // Update statuses
            this.updateVitalStatus('bloodPressureStatus', this.getBloodPressureStatus(systolic, diastolic));
            this.updateVitalStatus('bloodOxygenStatus', 'Excellent');
            this.updateVitalStatus('temperatureStatus', 'Normal');
        }
    }

    updateVitalStatus(elementId, status) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = status;
            element.className = `status-indicator status-${status.toLowerCase().replace(' ', '-')}`;
        }
    }

    updateDeviceStatus(data) {
        const deviceInfo = document.getElementById('deviceInfo');
        const deviceCount = document.getElementById('deviceCount');
        
        // Simulate device connections based on data availability
        const hasData = data.raw_data && (
            data.raw_data.heart_rate?.length > 0 || 
            data.raw_data.activity?.length > 0 || 
            data.raw_data.sleep?.length > 0
        );
        
        if (hasData) {
            const devices = this.generateDeviceList(data);
            if (deviceInfo) {
                deviceInfo.innerHTML = devices.map(device => `
                    <div class="device-item">
                        <div class="device-name">${device.name}</div>
                        <div class="device-status">
                            <span class="status-indicator status-${device.status.toLowerCase()}">${device.status}</span>
                            <span class="battery-level">Battery: ${device.battery}%</span>
                        </div>
                        <div class="device-sync">Last sync: ${device.lastSync}</div>
                    </div>
                `).join('');
            }
            
            if (deviceCount) {
                deviceCount.textContent = `${devices.length} device${devices.length !== 1 ? 's' : ''}`;
            }
        } else {
            if (deviceInfo) {
                deviceInfo.innerHTML = `
                    <div class="no-devices">
                        <p>No devices connected</p>
                        <button class="scan-devices-btn" id="scanDevicesBtn">🔍 Scan for Devices</button>
                    </div>
                `;
            }
            if (deviceCount) deviceCount.textContent = '0 devices';
        }
    }

    updateConnectionStatus(isConnected) {
        const connectionStatus = document.getElementById('connectionStatus');
        if (connectionStatus) {
            const statusDot = connectionStatus.querySelector('.status-dot');
            const statusText = connectionStatus.querySelector('.status-text');
            
            if (isConnected) {
                statusDot.className = 'status-dot connected';
                statusText.textContent = 'Connected';
            } else {
                statusDot.className = 'status-dot disconnected';
                statusText.textContent = 'Disconnected';
            }
        }
    }

    // Helper methods for status calculations
    getHeartRateStatus(hr) {
        if (hr < 60) return 'Low';
        if (hr > 100) return 'High';
        return 'Normal';
    }

    getHeartRateStatusClass(hr) {
        if (hr < 60 || hr > 100) return 'status-warning';
        return 'status-normal';
    }

    getSleepHoursStatus(hours) {
        if (hours < 6) return 'Too Little';
        if (hours > 9) return 'Too Much';
        if (hours >= 7 && hours <= 8) return 'Excellent';
        return 'Good';
    }

    getSleepHoursStatusClass(hours) {
        if (hours < 6 || hours > 9) return 'status-warning';
        if (hours >= 7 && hours <= 8) return 'status-excellent';
        return 'status-normal';
    }

    getSleepEfficiencyStatus(efficiency) {
        if (efficiency >= 90) return 'Excellent';
        if (efficiency >= 80) return 'Good';
        if (efficiency >= 70) return 'Fair';
        return 'Poor';
    }

    getSleepEfficiencyStatusClass(efficiency) {
        if (efficiency >= 90) return 'status-excellent';
        if (efficiency >= 80) return 'status-normal';
        if (efficiency >= 70) return 'status-warning';
        return 'status-critical';
    }

    getBloodPressureStatus(systolic, diastolic) {
        if (systolic >= 140 || diastolic >= 90) return 'High';
        if (systolic < 90 || diastolic < 60) return 'Low';
        return 'Normal';
    }

    calculateHealthScore(summary) {
        let score = 50; // Base score
        
        // Heart rate contribution (20 points)
        if (summary.heart_rate && summary.heart_rate.avg_heart_rate) {
            const hr = summary.heart_rate.avg_heart_rate;
            if (hr >= 60 && hr <= 100) score += 20;
            else if (hr >= 50 && hr <= 110) score += 15;
            else score += 5;
        }
        
        // Activity contribution (20 points)
        if (summary.activity && summary.activity.avg_steps) {
            const steps = summary.activity.avg_steps;
            if (steps >= 10000) score += 20;
            else if (steps >= 7500) score += 15;
            else if (steps >= 5000) score += 10;
            else score += 5;
        }
        
        // Sleep contribution (20 points)
        if (summary.sleep && summary.sleep.avg_sleep_duration) {
            const hours = summary.sleep.avg_sleep_duration / 60;
            if (hours >= 7 && hours <= 8) score += 20;
            else if (hours >= 6 && hours <= 9) score += 15;
            else score += 5;
        }
        
        // Sleep efficiency contribution (10 points)
        if (summary.sleep && summary.sleep.avg_sleep_efficiency) {
            const efficiency = summary.sleep.avg_sleep_efficiency;
            if (efficiency >= 90) score += 10;
            else if (efficiency >= 80) score += 7;
            else if (efficiency >= 70) score += 5;
        }
        
        return Math.min(Math.max(score, 0), 100);
    }

    generateHealthScoreDescription(score, summary) {
        if (score >= 90) {
            return "Excellent! Your health metrics are outstanding. Keep up the great work with your current routine.";
        } else if (score >= 80) {
            return "Very good! Your health indicators are strong. Minor improvements could optimize your wellness further.";
        } else if (score >= 70) {
            return "Good overall health. There are some areas where small changes could make a significant impact.";
        } else if (score >= 60) {
            return "Fair health status. Consider focusing on the recommendations below to improve your wellness.";
        } else {
            return "Your health metrics suggest room for improvement. Please consider consulting with a healthcare professional.";
        }
    }

    generateRecommendations(summary) {
        const recommendations = [];
        
        // Heart rate recommendations
        if (summary.heart_rate && summary.heart_rate.avg_heart_rate) {
            const hr = summary.heart_rate.avg_heart_rate;
            if (hr > 100) {
                recommendations.push({
                    icon: "🧘",
                    text: "Try relaxation techniques to lower your resting heart rate"
                });
            } else if (hr < 60) {
                recommendations.push({
                    icon: "🏃",
                    text: "Consider light cardio exercise to improve heart health"
                });
            }
        }
        
        // Activity recommendations
        if (summary.activity && summary.activity.avg_steps) {
            const steps = summary.activity.avg_steps;
            if (steps < 7500) {
                recommendations.push({
                    icon: "🚶",
                    text: `Add ${Math.ceil((7500 - steps) / 100) * 100} more steps daily for better health`
                });
            } else if (steps >= 10000) {
                recommendations.push({
                    icon: "🎯",
                    text: "Great job on staying active! Maintain this excellent routine"
                });
            }
        }
        
        // Sleep recommendations
        if (summary.sleep && summary.sleep.avg_sleep_duration) {
            const hours = summary.sleep.avg_sleep_duration / 60;
            if (hours < 7) {
                recommendations.push({
                    icon: "😴",
                    text: "Aim for 7-8 hours of sleep nightly for optimal recovery"
                });
            } else if (hours > 9) {
                recommendations.push({
                    icon: "⏰",
                    text: "Consider a more consistent sleep schedule to improve sleep quality"
                });
            }
        }
        
        // Default recommendations if no specific data
        if (recommendations.length === 0) {
            recommendations.push(
                { icon: "💧", text: "Stay hydrated - aim for 8 glasses of water daily" },
                { icon: "🥗", text: "Include more fruits and vegetables in your diet" },
                { icon: "🧘", text: "Practice mindfulness or meditation for 10 minutes daily" }
            );
        }
        
        return recommendations;
    }

    calculateConfidence(summary) {
        let confidence = 0;
        let factors = 0;
        
        if (summary.heart_rate && summary.heart_rate.avg_heart_rate) {
            confidence += 25;
            factors++;
        }
        
        if (summary.activity && summary.activity.avg_steps) {
            confidence += 25;
            factors++;
        }
        
        if (summary.sleep && summary.sleep.avg_sleep_duration) {
            confidence += 25;
            factors++;
        }
        
        if (summary.sleep && summary.sleep.avg_sleep_efficiency) {
            confidence += 25;
            factors++;
        }
        
        return factors > 0 ? Math.round(confidence / factors * factors) : 50;
    }

    generateDeviceList(data) {
        const devices = [];
        
        if (data.raw_data.heart_rate && data.raw_data.heart_rate.length > 0) {
            devices.push({
                name: "Fitness Tracker",
                status: "Connected",
                battery: Math.floor(Math.random() * 30) + 70,
                lastSync: this.getRelativeTime(new Date(Date.now() - Math.random() * 300000))
            });
        }
        
        if (data.raw_data.sleep && data.raw_data.sleep.length > 0) {
            devices.push({
                name: "Sleep Monitor",
                status: "Connected",
                battery: Math.floor(Math.random() * 40) + 60,
                lastSync: this.getRelativeTime(new Date(Date.now() - Math.random() * 600000))
            });
        }
        
        return devices;
    }

    generateTrendIndicator(metric, value) {
        // Simulate trend based on current value (in real app, compare with historical data)
        const trends = ['📈', '📉', '➡️'];
        const trend = trends[Math.floor(Math.random() * trends.length)];
        const change = (Math.random() * 10 - 5).toFixed(1);
        
        return `<span class="trend-indicator">${trend} ${change > 0 ? '+' : ''}${change}%</span>`;
    }

    getTimeOfDay() {
        const hour = new Date().getHours();
        if (hour < 12) return 'morning';
        if (hour < 17) return 'afternoon';
        return 'evening';
    }

    getRelativeTime(date) {
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        
        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
        
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;
        
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`;
    }

    updateLastUpdatedTime() {
        const lastUpdatedEl = document.getElementById('lastUpdated');
        if (lastUpdatedEl && this.lastUpdate) {
            lastUpdatedEl.textContent = this.getRelativeTime(new Date(this.lastUpdate));
        }
    }

    showLoading(show) {
        const loadingSpinner = document.getElementById('loadingSpinner');
        const dashboardPage = document.getElementById('dashboardPage');
        
        if (loadingSpinner) {
            loadingSpinner.classList.toggle('active', show);
        }
        if (dashboardPage) {
            dashboardPage.classList.toggle('active', !show);
        }
    }

    showError(message) {
        const errorMessage = document.getElementById('errorMessage');
        const errorText = document.getElementById('errorText');
        
        if (errorMessage) errorMessage.style.display = 'block';
        if (errorText) errorText.textContent = message;
        
        this.updateConnectionStatus(false);
    }

    hideError() {
        const errorMessage = document.getElementById('errorMessage');
        if (errorMessage) errorMessage.style.display = 'none';
    }

    loadFallbackData() {
        // Load demo data when API fails
        const fallbackData = {
            summary: {
                heart_rate: { avg_heart_rate: 72, max_heart_rate: 95, min_heart_rate: 58 },
                activity: { avg_steps: 8547, avg_calories: 2150, avg_active_minutes: 45 },
                sleep: { avg_sleep_duration: 450, avg_sleep_efficiency: 82 }
            },
            raw_data: {
                heart_rate: [{ heart_rate: 72, timestamp: new Date().toISOString() }],
                activity: [{ total_steps: 8547, calories: 2150, date: new Date().toISOString() }],
                sleep: Array.from({ length: 7 }, (_, i) => ({
                    date: new Date(Date.now() - i * 24 * 60 * 60 * 1000).toISOString(),
                    total_minutes_asleep: 420 + Math.random() * 60,
                    sleep_efficiency: 80 + Math.random() * 15
                }))
            }
        };
        
        this.updateDashboard(fallbackData);
        this.showNotification('Using demo data - check your connection', 'warning');
    }

    showNotification(message, type = 'info') {
        const container = document.getElementById('notificationContainer');
        if (!container) return;
        
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span class="notification-message">${message}</span>
            <button class="notification-close">×</button>
        `;
        
        container.appendChild(notification);
        
        notification.querySelector('.notification-close').addEventListener('click', () => {
            notification.remove();
        });
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    startAutoRefresh() {
        // Refresh every 5 minutes
        this.refreshInterval = setInterval(() => {
            this.loadDashboardData();
            this.updateLastUpdatedTime();
        }, 300000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    // Quick action methods
    async startWorkout() {
        this.showNotification('Starting workout tracking...', 'info');
        // Implementation for workout tracking
    }

    async logMedicine() {
        this.showNotification('Opening medicine log...', 'info');
        // Implementation for medicine logging
    }

    async emergencyContact() {
        this.showNotification('Initiating emergency protocol...', 'warning');
        // Implementation for emergency contact
    }

    async exportData() {
        try {
            const response = await fetch(`/api/export/${this.userId}`, {
                credentials: 'include'
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = `health-data-${new Date().toISOString().split('T')[0]}.csv`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                this.showNotification('Data exported successfully!', 'success');
            } else {
                throw new Error('Export failed');
            }
        } catch (error) {
            this.showNotification('Failed to export data', 'error');
        }
    }

    async scanForDevices() {
        this.showNotification('Scanning for devices...', 'info');
        try {
            const response = await fetch('/api/wearable/scan', {
                method: 'POST',
                credentials: 'include'
            });
            
            if (response.ok) {
                this.showNotification('Device scan completed', 'success');
                setTimeout(() => this.loadDashboardData(), 2000);
            }
        } catch (error) {
            this.showNotification('Device scan failed', 'error');
        }
    }

    logout() {
        if (confirm('Are you sure you want to logout?')) {
            this.stopAutoRefresh();
            sessionStorage.clear();
            window.location.href = '/logout';
        }
    }

    destroy() {
        this.stopAutoRefresh();
        Object.values(this.charts).forEach(chart => chart.destroy());
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboardManager = new DashboardManager();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.dashboardManager) {
        window.dashboardManager.destroy();
    }
});