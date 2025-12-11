// Mode toggle functionality
document.addEventListener('DOMContentLoaded', function() {
    const modeToggle = document.querySelector('.mode-controller');
    const modeBadge = document.getElementById('mode-badge');
    
    if (!modeToggle || !modeBadge) {
        console.error('[Mode] Required elements not found');
        return;
    }

    // State management variables
    let isInitialized = false;
    let currentMode = false; // false = Live Mode, true = Analyze Mode

    function updateBadge(isAnalyzeMode, skipThemeChange = false) {
        // Prevent unnecessary updates if mode hasn't actually changed
        if (isInitialized && currentMode === isAnalyzeMode) {
            return;
        }

        currentMode = isAnalyzeMode;

        // Only update toggle state if it's different to prevent icon flip
        if (modeToggle.checked !== isAnalyzeMode) {
            modeToggle.checked = isAnalyzeMode;
        }

        // Clear all badge classes first
        modeBadge.classList.remove('badge-success', 'badge-warning', 'badge-neutral');

        // Hide theme switcher BEFORE theme change to prevent icon flip
        const themeSwitcher = document.querySelector('.theme-switcher');
        if (!skipThemeChange && themeSwitcher) {
            themeSwitcher.style.transition = 'none';
            themeSwitcher.style.opacity = '0';
        }

        // Check if mobile (screen width < 640px)
        const isMobile = window.innerWidth < 640;

        if (isAnalyzeMode) {
            modeBadge.textContent = isMobile ? 'Analyze' : 'Analyze Mode';
            modeBadge.classList.add('badge-warning');
            modeBadge.style.opacity = '1';

            if (!skipThemeChange && window.themeManager) {
                // Store current theme before switching to dracula (analyze theme)
                const currentTheme = document.documentElement.getAttribute('data-theme');
                if (currentTheme !== 'dracula') {
                    localStorage.setItem('previousTheme', currentTheme);
                    sessionStorage.setItem('previousTheme', currentTheme);
                }
                window.themeManager.setTheme('dracula');
            }
        } else {
            modeBadge.textContent = isMobile ? 'Live' : 'Live Mode';
            modeBadge.classList.add('badge-success');
            modeBadge.style.opacity = '1';

            if (!skipThemeChange && window.themeManager) {
                // Only restore theme if we're switching from dracula (analyze) mode
                const currentTheme = document.documentElement.getAttribute('data-theme');
                if (currentTheme === 'dracula') {
                    window.themeManager.restorePreviousTheme();
                }
            }
        }

        // Show theme switcher after theme change is complete
        if (!skipThemeChange && themeSwitcher) {
            setTimeout(() => {
                themeSwitcher.style.transition = '';
                themeSwitcher.style.opacity = '1';
            }, 10);
        }

        // Update session storage
        sessionStorage.setItem('analyzeMode', isAnalyzeMode.toString());
        localStorage.setItem('analyzeMode', isAnalyzeMode.toString()); // For cross-tab sync
    }

    // Initialize mode from server (authoritative source)
    function initializeFromServer() {
        fetch('/settings/analyze-mode')
            .then(response => response.json())
            .then(data => {
                const serverMode = Boolean(data.analyze_mode);
                updateBadge(serverMode);
                isInitialized = true;
            })
            .catch(error => {
                console.error('[Mode] Error fetching analyze mode:', error);
                // Fallback to Live Mode if server fetch fails
                updateBadge(false);
                isInitialized = true;
            });
    }
    
    // Initialize immediately
    initializeFromServer();

    // Handle mode toggle
    modeToggle.addEventListener('change', function(e) {
        // Prevent multiple rapid clicks
        if (!isInitialized) {
            e.target.checked = currentMode;
            return;
        }
        
        const newMode = e.target.checked ? 1 : 0;
        const newModeBoolean = Boolean(newMode);
        
        // Optimistically update UI
        updateBadge(newModeBoolean);
        
        fetch(`/settings/analyze-mode/${newMode}`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Ensure UI matches server response
                updateBadge(Boolean(data.analyze_mode));
                showToast(data.message, 'success');

                // Show disclaimer toast when enabling analyzer mode
                if (newModeBoolean === true) {
                    setTimeout(() => {
                        showToast('⚠️ Analyzer (Sandbox) mode is for testing purposes only', 'warning', 20000);
                    }, 2000); // Slight delay to show after success toast
                }

                // Refresh current page content to reflect the mode change
                // Use the refreshCurrentPageContent function if available
                if (typeof refreshCurrentPageContent === 'function') {
                    setTimeout(() => {
                        refreshCurrentPageContent();
                    }, 500); // Small delay to ensure mode is properly set
                } else {
                    // Fallback: reload the page if refresh function is not available
                    setTimeout(() => {
                        window.location.reload();
                    }, 500);
                }
            } else {
                throw new Error(data.error || 'Unknown error');
            }
        })
        .catch(error => {
            console.error('[Mode] Error updating mode:', error);
            showToast('Failed to update mode', 'error');

            // Revert to previous state on error
            updateBadge(!newModeBoolean);
        });
    });

    // Handle page visibility changes - re-sync with server when page becomes visible
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden && isInitialized) {
            // Re-sync with server when page becomes visible
            initializeFromServer();
        }
    });

    // Handle storage events for cross-tab consistency
    window.addEventListener('storage', function(e) {
        if (e.key === 'analyzeMode' && isInitialized) {
            const isAnalyzeMode = e.newValue === 'true';
            updateBadge(isAnalyzeMode, true); // Skip theme change for storage events
        }
    });

    // Handle window resize to update badge text for mobile/desktop
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            if (isInitialized && modeBadge) {
                const isMobile = window.innerWidth < 640;
                if (currentMode) {
                    modeBadge.textContent = isMobile ? 'Analyze' : 'Analyze Mode';
                } else {
                    modeBadge.textContent = isMobile ? 'Live' : 'Live Mode';
                }
            }
        }, 100); // Debounce resize events
    });
});

// Data mode toggle functionality (Live vs Historical Data)
document.addEventListener('DOMContentLoaded', function() {
    const dataModeToggle = document.querySelector('.data-mode-controller');
    const dataModeBadge = document.getElementById('data-mode-badge');
    
    if (!dataModeToggle || !dataModeBadge) {
        // Elements might not exist on all pages, silently return
        return;
    }

    // State management variables
    let isDataModeInitialized = false;
    let currentDataMode = false; // false = Live Data, true = Historical Data

    function updateDataModeBadge(useHistorical, skipUpdate = false) {
        // Prevent unnecessary updates if mode hasn't actually changed
        if (isDataModeInitialized && currentDataMode === useHistorical) {
            return;
        }

        currentDataMode = useHistorical;

        // Only update toggle state if it's different
        if (dataModeToggle.checked !== useHistorical) {
            dataModeToggle.checked = useHistorical;
        }

        // Clear all badge classes first
        dataModeBadge.classList.remove('badge-success', 'badge-info', 'badge-neutral');

        // Check if mobile (screen width < 640px)
        const isMobile = window.innerWidth < 640;

        if (useHistorical) {
            dataModeBadge.textContent = isMobile ? 'Historical' : 'Historical Data';
            dataModeBadge.classList.add('badge-info');
        } else {
            dataModeBadge.textContent = isMobile ? 'Live' : 'Live Data';
            dataModeBadge.classList.add('badge-success');
        }
        dataModeBadge.style.opacity = '1';

        // Update session storage
        sessionStorage.setItem('useHistoricalData', useHistorical.toString());
        localStorage.setItem('useHistoricalData', useHistorical.toString()); // For cross-tab sync
    }

    // Initialize data mode from server (authoritative source)
    function initializeDataModeFromServer() {
        fetch('/settings/data-mode')
            .then(response => response.json())
            .then(data => {
                const serverDataMode = Boolean(data.use_historical_data);
                updateDataModeBadge(serverDataMode);
                isDataModeInitialized = true;
            })
            .catch(error => {
                console.error('[Data Mode] Error fetching data mode:', error);
                // Fallback to Live Data if server fetch fails
                updateDataModeBadge(false);
                isDataModeInitialized = true;
            });
    }
    
    // Initialize immediately
    initializeDataModeFromServer();

    // Handle data mode toggle
    dataModeToggle.addEventListener('change', function(e) {
        // Prevent multiple rapid clicks
        if (!isDataModeInitialized) {
            e.target.checked = currentDataMode;
            return;
        }
        
        const newDataMode = e.target.checked ? 1 : 0;
        const newDataModeBoolean = Boolean(newDataMode);
        
        // Optimistically update UI
        updateDataModeBadge(newDataModeBoolean);
        
        fetch(`/settings/data-mode/${newDataMode}`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Ensure UI matches server response
                updateDataModeBadge(Boolean(data.use_historical_data));
                showToast(data.message, 'success');

                // Show info toast when switching modes
                if (newDataModeBoolean === true) {
                    setTimeout(() => {
                        showToast('📊 Historical Data Mode: Square-off restrictions disabled for testing', 'info', 10000);
                    }, 2000);
                } else {
                    setTimeout(() => {
                        showToast('📡 Live Data Mode: Square-off restrictions enforced', 'info', 10000);
                    }, 2000);
                }
            } else {
                throw new Error(data.error || 'Unknown error');
            }
        })
        .catch(error => {
            console.error('[Data Mode] Error updating data mode:', error);
            showToast('Failed to update data mode', 'error');

            // Revert to previous state on error
            updateDataModeBadge(!newDataModeBoolean);
        });
    });

    // Handle page visibility changes - re-sync with server when page becomes visible
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden && isDataModeInitialized) {
            // Re-sync with server when page becomes visible
            initializeDataModeFromServer();
        }
    });

    // Handle storage events for cross-tab consistency
    window.addEventListener('storage', function(e) {
        if (e.key === 'useHistoricalData' && isDataModeInitialized) {
            const useHistorical = e.newValue === 'true';
            updateDataModeBadge(useHistorical, true);
        }
    });

    // Handle window resize to update badge text for mobile/desktop
    let dataModeResizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(dataModeResizeTimer);
        dataModeResizeTimer = setTimeout(function() {
            if (isDataModeInitialized && dataModeBadge) {
                const isMobile = window.innerWidth < 640;
                if (currentDataMode) {
                    dataModeBadge.textContent = isMobile ? 'Historical' : 'Historical Data';
                } else {
                    dataModeBadge.textContent = isMobile ? 'Live' : 'Live Data';
                }
            }
        }, 100); // Debounce resize events
    });
});