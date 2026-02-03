"""Anti-detection scripts and configurations for browser automation"""


class BrowserAntiDetection:
    """Browser anti-detection utilities"""

    # Browser launch arguments
    BROWSER_ARGS = [
        "--disable-blink-features=AutomationControlled",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--start-maximized",
    ]

    # Browser context configuration
    CONTEXT_CONFIG = {
        "no_viewport": True,
        "locale": "uk-UA",
        "timezone_id": "Europe/Kyiv",
        "permissions": ["geolocation"],
        "geolocation": {"latitude": 50.4501, "longitude": 30.5234},  # Kyiv
        "color_scheme": "light",
        "has_touch": False,
        "is_mobile": False,
    }

    @staticmethod
    def get_init_script() -> str:
        """Get JavaScript initialization script for anti-detection

        Returns:
            JavaScript code as string to inject into page
        """
        return """
            // 1. Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // 2. Add chrome object
            window.chrome = {
                runtime: {},
                loadTimes: function() {},
                csi: function() {},
                app: {}
            };
            
            // 3. Permissions API
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // 4. Plugins - make realistic
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // 5. Languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['uk-UA', 'uk', 'en-US', 'en']
            });
            
            // 6. Platform
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32'
            });
            
            // 7. Remove playwright markers
            delete window.__playwright;
            delete window.__pw_manual;
            delete window.__PW_inspect;
            
            // 8. Remove driver property
            Object.defineProperty(navigator, 'driver', {
                get: () => undefined
            });
            
            // 9. Battery API - realistic
            Object.defineProperty(navigator, 'getBattery', {
                get: () => async () => ({
                    charging: true,
                    chargingTime: 0,
                    dischargingTime: Infinity,
                    level: 1
                })
            });
            
            // 10. Connection API
            Object.defineProperty(navigator, 'connection', {
                get: () => ({
                    effectiveType: '4g',
                    downlink: 10,
                    rtt: 50
                })
            });
            
            // 11. Hardware Concurrency
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8
            });
            
            // 12. Memory (if exists)
            if ('deviceMemory' in navigator) {
                Object.defineProperty(navigator, 'deviceMemory', {
                    get: () => 8
                });
            }
            
            // 13. Hide automation-controlled
            const originalEval = window.eval;
            window.eval = function() {
                return originalEval.apply(this, arguments);
            };
            
            // 14. toString override
            window.eval.toString = () => 'function eval() { [native code] }';
        """
