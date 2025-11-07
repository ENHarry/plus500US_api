"""
Performance monitoring and optimization for WebDriver operations.

This module provides comprehensive performance monitoring, resource cleanup,
and optimization utilities for WebDriver operations in the Plus500US client.
"""

import time
import psutil
import logging
import threading
from typing import Dict, List, Optional, Any, ContextManager
from contextlib import contextmanager
from pathlib import Path
from dataclasses import dataclass, field
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService

from ..security import secure_logger

logger = secure_logger(__name__)

@dataclass
class PerformanceMetrics:
    """Performance metrics for WebDriver operations"""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration: Optional[float] = None
    memory_before: Optional[float] = None
    memory_after: Optional[float] = None
    memory_peak: Optional[float] = None
    cpu_usage: List[float] = field(default_factory=list)
    network_requests: int = 0
    page_load_time: Optional[float] = None
    operation_type: str = ""
    success: bool = True
    error_message: Optional[str] = None

    def finalize(self):
        """Finalize metrics calculation"""
        if self.end_time is None:
            self.end_time = time.time()
        self.duration = self.end_time - self.start_time

class ResourceMonitor:
    """Monitor system resources during WebDriver operations"""
    
    def __init__(self, interval: float = 0.5):
        self.interval = interval
        self.monitoring = False
        self.metrics: List[Dict[str, float]] = []
        self._monitor_thread: Optional[threading.Thread] = None
    
    def start_monitoring(self):
        """Start resource monitoring"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.metrics.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.debug("Started resource monitoring")
    
    def stop_monitoring(self) -> Dict[str, Any]:
        """Stop monitoring and return collected metrics"""
        if not self.monitoring:
            return {}
        
        self.monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)
        
        logger.debug(f"Stopped resource monitoring, collected {len(self.metrics)} samples")
        return self._analyze_metrics()
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                memory_info = psutil.virtual_memory()
                cpu_percent = psutil.cpu_percent(interval=None)
                
                self.metrics.append({
                    'timestamp': time.time(),
                    'memory_percent': memory_info.percent,
                    'memory_available_gb': memory_info.available / (1024**3),
                    'cpu_percent': cpu_percent
                })
                
                time.sleep(self.interval)
            except Exception as e:
                logger.warning(f"Error in resource monitoring: {e}")
                break
    
    def _analyze_metrics(self) -> Dict[str, Any]:
        """Analyze collected metrics"""
        if not self.metrics:
            return {}
        
        memory_values = [m['memory_percent'] for m in self.metrics]
        cpu_values = [m['cpu_percent'] for m in self.metrics]
        
        return {
            'samples': len(self.metrics),
            'memory': {
                'avg': sum(memory_values) / len(memory_values),
                'max': max(memory_values),
                'min': min(memory_values)
            },
            'cpu': {
                'avg': sum(cpu_values) / len(cpu_values),
                'max': max(cpu_values),
                'min': min(cpu_values)
            },
            'duration': self.metrics[-1]['timestamp'] - self.metrics[0]['timestamp']
        }

class WebDriverOptimizer:
    """Optimize WebDriver performance and resource usage"""
    
    def __init__(self):
        self.active_drivers: Dict[str, WebDriver] = {}
        self.driver_services: Dict[str, Any] = {}
        self.performance_cache: Dict[str, Any] = {}
    
    def optimize_browser_config(self, browser_type: str = "chrome") -> Dict[str, Any]:
        """Get optimized browser configuration for performance"""
        base_config = {
            'page_load_strategy': 'eager',  # Don't wait for all resources
            'timeouts': {
                'implicit': 5,
                'page_load': 30,
                'script': 30
            }
        }
        
        if browser_type.lower() == "chrome":
            return {
                **base_config,
                'chrome_options': [
                    '--disable-gpu',
                    '--disable-dev-shm-usage',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-images',  # Faster loading
                    '--disable-javascript',  # For static content only
                    '--no-sandbox',
                    '--disable-web-security',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--memory-pressure-off',
                    '--aggressive-cache-discard',
                    '--max_old_space_size=2048'
                ]
            }
        elif browser_type.lower() == "firefox":
            return {
                **base_config,
                'firefox_prefs': {
                    'dom.webnotifications.enabled': False,
                    'media.autoplay.default': 2,
                    'permissions.default.image': 2,  # Block images
                    'javascript.enabled': False,  # For static content
                    'browser.cache.memory.enable': False,
                    'browser.cache.disk.enable': False
                }
            }
        
        return base_config
    
    def register_driver(self, driver_id: str, driver: WebDriver, service: Any = None):
        """Register a WebDriver for tracking and cleanup"""
        self.active_drivers[driver_id] = driver
        if service:
            self.driver_services[driver_id] = service
        logger.debug(f"Registered WebDriver: {driver_id}")
    
    def cleanup_driver(self, driver_id: str) -> bool:
        """Clean up a specific WebDriver and its resources"""
        try:
            # Close driver
            if driver_id in self.active_drivers:
                driver = self.active_drivers[driver_id]
                try:
                    driver.quit()
                except Exception as e:
                    logger.warning(f"Error closing driver {driver_id}: {e}")
                del self.active_drivers[driver_id]
            
            # Stop service
            if driver_id in self.driver_services:
                service = self.driver_services[driver_id]
                try:
                    if hasattr(service, 'stop'):
                        service.stop()
                except Exception as e:
                    logger.warning(f"Error stopping service {driver_id}: {e}")
                del self.driver_services[driver_id]
            
            logger.info(f"Successfully cleaned up WebDriver: {driver_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error cleaning up WebDriver {driver_id}: {e}")
            return False
    
    def cleanup_all_drivers(self) -> Dict[str, bool]:
        """Clean up all registered WebDrivers"""
        results = {}
        driver_ids = list(self.active_drivers.keys())
        
        for driver_id in driver_ids:
            results[driver_id] = self.cleanup_driver(driver_id)
        
        logger.info(f"Cleaned up {len(driver_ids)} WebDrivers")
        return results
    
    def get_memory_usage(self) -> Dict[str, float]:
        """Get current memory usage statistics"""
        memory_info = psutil.virtual_memory()
        return {
            'total_gb': memory_info.total / (1024**3),
            'available_gb': memory_info.available / (1024**3),
            'used_gb': memory_info.used / (1024**3),
            'percent': memory_info.percent
        }
    
    def optimize_for_headless(self, browser_config: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize configuration for headless mode"""
        optimized = browser_config.copy()
        
        if 'chrome_options' in optimized:
            optimized['chrome_options'].extend([
                '--headless=new',
                '--disable-gpu',
                '--virtual-time-budget=1000',
                '--run-all-compositor-stages-before-draw'
            ])
        elif 'firefox_prefs' in optimized:
            optimized['firefox_prefs'].update({
                'general.useragent.override': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
                'dom.webdriver.enabled': False
            })
        
        return optimized

class PerformanceProfiler:
    """Profile WebDriver operations for performance analysis"""
    
    def __init__(self):
        self.profiles: Dict[str, PerformanceMetrics] = {}
        self.resource_monitor = ResourceMonitor()
    
    @contextmanager
    def profile_operation(self, operation_name: str) -> ContextManager[PerformanceMetrics]:
        """Context manager for profiling WebDriver operations"""
        metrics = PerformanceMetrics(operation_type=operation_name)
        metrics.memory_before = psutil.virtual_memory().percent
        
        self.resource_monitor.start_monitoring()
        
        try:
            yield metrics
            metrics.success = True
        except Exception as e:
            metrics.success = False
            metrics.error_message = str(e)
            raise
        finally:
            metrics.memory_after = psutil.virtual_memory().percent
            resource_stats = self.resource_monitor.stop_monitoring()
            
            if resource_stats:
                metrics.memory_peak = resource_stats['memory']['max']
                metrics.cpu_usage = [resource_stats['cpu']['avg']]
            
            metrics.finalize()
            self.profiles[operation_name] = metrics
            
            logger.info(f"Operation '{operation_name}' completed in {metrics.duration:.2f}s "
                       f"(success: {metrics.success})")
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        if not self.profiles:
            return {"message": "No performance data available"}
        
        total_operations = len(self.profiles)
        successful_operations = sum(1 for m in self.profiles.values() if m.success)
        
        durations = [m.duration for m in self.profiles.values() if m.duration]
        memory_usage = [m.memory_peak for m in self.profiles.values() if m.memory_peak]
        
        report = {
            'summary': {
                'total_operations': total_operations,
                'successful_operations': successful_operations,
                'success_rate': successful_operations / total_operations * 100,
                'total_duration': sum(durations)
            },
            'performance': {
                'avg_duration': sum(durations) / len(durations) if durations else 0,
                'max_duration': max(durations) if durations else 0,
                'min_duration': min(durations) if durations else 0
            },
            'memory': {
                'avg_peak_usage': sum(memory_usage) / len(memory_usage) if memory_usage else 0,
                'max_peak_usage': max(memory_usage) if memory_usage else 0
            },
            'operations': {
                name: {
                    'duration': metrics.duration,
                    'success': metrics.success,
                    'memory_peak': metrics.memory_peak,
                    'error': metrics.error_message
                }
                for name, metrics in self.profiles.items()
            }
        }
        
        return report
    
    def clear_profiles(self):
        """Clear all performance profiles"""
        self.profiles.clear()
        logger.info("Cleared all performance profiles")

class StartupOptimizer:
    """Optimize WebDriver startup and teardown processes"""
    
    @staticmethod
    def get_fast_startup_config(browser_type: str = "chrome") -> Dict[str, Any]:
        """Get configuration optimized for fast startup"""
        base_config = {
            'page_load_strategy': 'none',  # Don't wait for page load
            'timeouts': {
                'implicit': 1,
                'page_load': 10,
                'script': 10
            }
        }
        
        if browser_type.lower() == "chrome":
            return {
                **base_config,
                'chrome_options': [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-images',
                    '--disable-background-timer-throttling',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-default-apps',
                    '--disable-sync',
                    '--disable-translate',
                    '--disable-web-security',
                    '--aggressive-cache-discard',
                    '--memory-pressure-off',
                    '--start-maximized'
                ]
            }
        
        return base_config
    
    @staticmethod
    def warmup_browser(driver: WebDriver, urls: List[str] = None) -> float:
        """Warm up browser with common operations"""
        start_time = time.time()
        
        try:
            # Navigate to a simple page first
            driver.get("data:text/html,<html><body>WebDriver Warmup</body></html>")
            
            # Perform common operations to warm up
            if urls:
                for url in urls[:3]:  # Limit to 3 URLs for warmup
                    try:
                        driver.get(url)
                        driver.find_element("tag name", "body")
                        break  # Success, stop warming up
                    except Exception:
                        continue
            
            # Execute a simple JavaScript to warm up JS engine
            driver.execute_script("return document.readyState;")
            
        except Exception as e:
            logger.warning(f"Browser warmup failed: {e}")
        
        warmup_time = time.time() - start_time
        logger.debug(f"Browser warmup completed in {warmup_time:.2f}s")
        return warmup_time

# Global instances
_optimizer = WebDriverOptimizer()
_profiler = PerformanceProfiler()

def get_optimizer() -> WebDriverOptimizer:
    """Get global WebDriver optimizer instance"""
    return _optimizer

def get_profiler() -> PerformanceProfiler:
    """Get global performance profiler instance"""
    return _profiler

def cleanup_all_resources():
    """Clean up all WebDriver resources"""
    try:
        results = _optimizer.cleanup_all_drivers()
        _profiler.clear_profiles()
        logger.info("All WebDriver resources cleaned up")
        return results
    except Exception as e:
        logger.error(f"Error during resource cleanup: {e}")
        return {}

# Performance monitoring decorator
def monitor_performance(operation_name: str = None):
    """Decorator to monitor performance of WebDriver operations"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            
            with _profiler.profile_operation(op_name) as metrics:
                result = func(*args, **kwargs)
                
                # Add custom metrics if result contains them
                if isinstance(result, dict) and 'performance_metrics' in result:
                    custom_metrics = result['performance_metrics']
                    if 'page_load_time' in custom_metrics:
                        metrics.page_load_time = custom_metrics['page_load_time']
                    if 'network_requests' in custom_metrics:
                        metrics.network_requests = custom_metrics['network_requests']
                
                return result
        
        return wrapper
    return decorator
