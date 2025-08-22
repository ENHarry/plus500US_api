"""
Tests for WebDriver ElementDetector component
"""
import pytest
from unittest.mock import Mock, patch
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, StaleElementReferenceException
)
from selenium.webdriver.common.by import By

from plus500us_client.webdriver.element_detector import ElementDetector


class TestElementDetector:
    """Test ElementDetector functionality"""
    
    def test_element_detector_initialization(self, mock_driver):
        """Test ElementDetector initializes correctly"""
        detector = ElementDetector(mock_driver)
        
        assert detector.driver == mock_driver
        assert detector.default_timeout == 10
        assert detector.default_poll_frequency == 0.5
    
    def test_find_element_robust_with_xpath(self, mock_driver):
        """Test find_element_robust with XPath selectors"""
        mock_element = Mock()
        mock_element.is_displayed.return_value = True
        mock_driver.find_element.return_value = mock_element
        
        detector = ElementDetector(mock_driver)
        
        selectors = {
            'xpath': ["//button[@id='test']", "//input[@name='test']"],
            'css': [".test-button"]
        }
        
        result = detector.find_element_robust(selectors)
        
        assert result == mock_element
        mock_driver.find_element.assert_called_with(By.XPATH, "//button[@id='test']")
    
    def test_find_element_robust_with_css(self, mock_driver):
        """Test find_element_robust with CSS selectors"""
        mock_element = Mock()
        mock_element.is_displayed.return_value = True
        
        # First XPath fails, CSS succeeds
        mock_driver.find_element.side_effect = [
            NoSuchElementException(), 
            mock_element
        ]
        
        detector = ElementDetector(mock_driver)
        
        selectors = {
            'xpath': ["//button[@id='test']"],
            'css': [".test-button", "#test-input"]
        }
        
        result = detector.find_element_robust(selectors)
        
        assert result == mock_element
        # Should have tried XPath first, then CSS
        assert mock_driver.find_element.call_count == 2
    
    def test_find_element_robust_fallback_through_selectors(self, mock_driver):
        """Test find_element_robust tries all selectors"""
        mock_element = Mock()
        mock_element.is_displayed.return_value = True
        
        # First two selectors fail, third succeeds
        mock_driver.find_element.side_effect = [
            NoSuchElementException(),
            NoSuchElementException(), 
            mock_element
        ]
        
        detector = ElementDetector(mock_driver)
        
        selectors = {
            'xpath': ["//button[@id='test1']", "//button[@id='test2']"],
            'css': [".test-button"]
        }
        
        result = detector.find_element_robust(selectors)
        
        assert result == mock_element
        assert mock_driver.find_element.call_count == 3
    
    def test_find_element_robust_returns_none_when_not_found(self, mock_driver):
        """Test find_element_robust returns None when element not found"""
        mock_driver.find_element.side_effect = NoSuchElementException()
        
        detector = ElementDetector(mock_driver)
        
        selectors = {
            'xpath': ["//button[@id='nonexistent']"],
            'css': [".nonexistent"]
        }
        
        result = detector.find_element_robust(selectors)
        
        assert result is None
    
    def test_find_element_robust_with_timeout(self, mock_driver):
        """Test find_element_robust respects timeout"""
        mock_driver.find_element.side_effect = NoSuchElementException()
        
        detector = ElementDetector(mock_driver)
        
        selectors = {
            'xpath': ["//button[@id='test']"]
        }
        
        with patch('time.time', side_effect=[0, 1, 2, 3, 6]):  # Simulate timeout after 5 seconds
            result = detector.find_element_robust(selectors, timeout=5)
        
        assert result is None
    
    def test_find_element_robust_wait_for_clickable(self, mock_driver):
        """Test find_element_robust waits for clickable element"""
        mock_element = Mock()
        mock_element.is_displayed.return_value = True
        mock_element.is_enabled.return_value = True
        mock_driver.find_element.return_value = mock_element
        
        detector = ElementDetector(mock_driver)
        
        selectors = {
            'xpath': ["//button[@id='test']"]
        }
        
        result = detector.find_element_robust(selectors, wait_for_clickable=True)
        
        assert result == mock_element
        mock_element.is_enabled.assert_called_once()
    
    def test_find_element_robust_waits_for_non_clickable_element(self, mock_driver):
        """Test find_element_robust waits when element not clickable"""
        mock_element = Mock()
        mock_element.is_displayed.return_value = True
        mock_element.is_enabled.side_effect = [False, False, True]  # Becomes enabled on third check
        mock_driver.find_element.return_value = mock_element
        
        detector = ElementDetector(mock_driver)
        
        selectors = {
            'xpath': ["//button[@id='test']"]
        }
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = detector.find_element_robust(selectors, wait_for_clickable=True, timeout=2)
        
        assert result == mock_element
        assert mock_element.is_enabled.call_count >= 2
    
    def test_wait_for_element_present(self, mock_driver):
        """Test wait_for_element when element becomes present"""
        mock_element = Mock()
        mock_driver.find_element.side_effect = [
            NoSuchElementException(),
            NoSuchElementException(),
            mock_element
        ]
        
        detector = ElementDetector(mock_driver)
        
        with patch('time.sleep'):  # Mock sleep
            result = detector.wait_for_element(By.XPATH, "//button[@id='test']", timeout=5)
        
        assert result == mock_element
        assert mock_driver.find_element.call_count == 3
    
    def test_wait_for_element_timeout(self, mock_driver):
        """Test wait_for_element timeout"""
        mock_driver.find_element.side_effect = NoSuchElementException()
        
        detector = ElementDetector(mock_driver)
        
        with patch('time.time', side_effect=[0, 1, 2, 6]):  # Timeout after 5 seconds
            with pytest.raises(TimeoutException):
                detector.wait_for_element(By.XPATH, "//button[@id='test']", timeout=5)
    
    def test_is_element_present_true(self, mock_driver):
        """Test is_element_present returns True when element exists"""
        mock_element = Mock()
        mock_driver.find_element.return_value = mock_element
        
        detector = ElementDetector(mock_driver)
        
        result = detector.is_element_present(By.XPATH, "//button[@id='test']")
        
        assert result is True
    
    def test_is_element_present_false(self, mock_driver):
        """Test is_element_present returns False when element doesn't exist"""
        mock_driver.find_element.side_effect = NoSuchElementException()
        
        detector = ElementDetector(mock_driver)
        
        result = detector.is_element_present(By.XPATH, "//button[@id='test']")
        
        assert result is False
    
    def test_extract_text_safe_with_text(self, mock_driver):
        """Test extract_text_safe with element containing text"""
        mock_element = Mock()
        mock_element.text = "Test Button"
        mock_element.get_attribute.return_value = None
        
        detector = ElementDetector(mock_driver)
        
        result = detector.extract_text_safe(mock_element)
        
        assert result == "Test Button"
    
    def test_extract_text_safe_with_value_attribute(self, mock_driver):
        """Test extract_text_safe with input element value"""
        mock_element = Mock()
        mock_element.text = ""
        mock_element.get_attribute.return_value = "Input Value"
        
        detector = ElementDetector(mock_driver)
        
        result = detector.extract_text_safe(mock_element)
        
        assert result == "Input Value"
        mock_element.get_attribute.assert_called_with("value")
    
    def test_extract_text_safe_with_innerHTML(self, mock_driver):
        """Test extract_text_safe falls back to innerHTML"""
        mock_element = Mock()
        mock_element.text = ""
        mock_element.get_attribute.side_effect = lambda attr: "Inner HTML" if attr == "innerHTML" else None
        
        detector = ElementDetector(mock_driver)
        
        result = detector.extract_text_safe(mock_element)
        
        assert result == "Inner HTML"
    
    def test_extract_text_safe_handles_stale_element(self, mock_driver):
        """Test extract_text_safe handles stale element reference"""
        mock_element = Mock()
        mock_element.text = Mock(side_effect=StaleElementReferenceException())
        
        detector = ElementDetector(mock_driver)
        
        result = detector.extract_text_safe(mock_element)
        
        assert result == ""
    
    def test_extract_text_safe_empty_element(self, mock_driver):
        """Test extract_text_safe with empty element"""
        mock_element = Mock()
        mock_element.text = ""
        mock_element.get_attribute.return_value = None
        
        detector = ElementDetector(mock_driver)
        
        result = detector.extract_text_safe(mock_element)
        
        assert result == ""
    
    def test_wait_for_clickable_element_ready(self, mock_driver):
        """Test wait_for_clickable when element is ready"""
        mock_element = Mock()
        mock_element.is_displayed.return_value = True
        mock_element.is_enabled.return_value = True
        
        detector = ElementDetector(mock_driver)
        
        result = detector.wait_for_clickable(mock_element, timeout=5)
        
        assert result is True
    
    def test_wait_for_clickable_element_becomes_ready(self, mock_driver):
        """Test wait_for_clickable when element becomes ready"""
        mock_element = Mock()
        mock_element.is_displayed.return_value = True
        mock_element.is_enabled.side_effect = [False, False, True]
        
        detector = ElementDetector(mock_driver)
        
        with patch('time.sleep'):
            result = detector.wait_for_clickable(mock_element, timeout=5)
        
        assert result is True
        assert mock_element.is_enabled.call_count >= 2
    
    def test_wait_for_clickable_timeout(self, mock_driver):
        """Test wait_for_clickable timeout"""
        mock_element = Mock()
        mock_element.is_displayed.return_value = True
        mock_element.is_enabled.return_value = False
        
        detector = ElementDetector(mock_driver)
        
        with patch('time.time', side_effect=[0, 1, 2, 6]):  # Timeout
            result = detector.wait_for_clickable(mock_element, timeout=5)
        
        assert result is False
    
    def test_wait_for_element_invisible(self, mock_driver):
        """Test wait_for_element_invisible"""
        mock_element = Mock()
        mock_element.is_displayed.side_effect = [True, True, False]
        mock_driver.find_element.return_value = mock_element
        
        detector = ElementDetector(mock_driver)
        
        with patch('time.sleep'):
            result = detector.wait_for_element_invisible(By.XPATH, "//div[@id='loading']", timeout=5)
        
        assert result is True
        assert mock_element.is_displayed.call_count >= 2
    
    def test_wait_for_element_invisible_not_present(self, mock_driver):
        """Test wait_for_element_invisible when element not present"""
        mock_driver.find_element.side_effect = NoSuchElementException()
        
        detector = ElementDetector(mock_driver)
        
        result = detector.wait_for_element_invisible(By.XPATH, "//div[@id='loading']", timeout=5)
        
        assert result is True  # Element not present means it's "invisible"
    
    def test_find_elements_robust(self, mock_driver):
        """Test find_elements_robust finds multiple elements"""
        mock_elements = [Mock(), Mock(), Mock()]
        mock_driver.find_elements.return_value = mock_elements
        
        detector = ElementDetector(mock_driver)
        
        selectors = {
            'xpath': ["//button[@class='test']"],
            'css': [".test-button"]
        }
        
        result = detector.find_elements_robust(selectors)
        
        assert result == mock_elements
        mock_driver.find_elements.assert_called_with(By.XPATH, "//button[@class='test']")
    
    def test_find_elements_robust_empty_list(self, mock_driver):
        """Test find_elements_robust returns empty list when no elements"""
        mock_driver.find_elements.return_value = []
        
        detector = ElementDetector(mock_driver)
        
        selectors = {
            'xpath': ["//button[@class='nonexistent']"]
        }
        
        result = detector.find_elements_robust(selectors)
        
        assert result == []
    
    def test_scroll_to_element(self, mock_driver):
        """Test scroll_to_element functionality"""
        mock_element = Mock()
        
        detector = ElementDetector(mock_driver)
        detector.scroll_to_element(mock_element)
        
        mock_driver.execute_script.assert_called_once()
        # Verify the JavaScript scroll command was executed
        call_args = mock_driver.execute_script.call_args[0]
        assert "scrollIntoView" in call_args[0]
    
    def test_highlight_element_for_debugging(self, mock_driver):
        """Test element highlighting for debugging"""
        mock_element = Mock()
        
        detector = ElementDetector(mock_driver)
        detector.highlight_element(mock_element)
        
        # Should execute JavaScript to highlight element
        mock_driver.execute_script.assert_called_once()
        call_args = mock_driver.execute_script.call_args[0]
        assert "style.border" in call_args[0] or "style.backgroundColor" in call_args[0]


@pytest.mark.webdriver 
class TestElementDetectorIntegration:
    """Integration tests for ElementDetector (require actual browser)"""
    
    @pytest.mark.slow
    def test_real_element_detection(self, real_browser_manager, browser_available):
        """Test element detection with real browser"""
        if not browser_available:
            pytest.skip("Browser not available")
        
        driver = real_browser_manager.get_driver()
        detector = ElementDetector(driver)
        
        # Navigate to a test page
        driver.get("data:text/html,<html><body><button id='test-btn'>Click Me</button></body></html>")
        
        selectors = {
            'xpath': ["//button[@id='test-btn']"],
            'css': ["#test-btn"]
        }
        
        element = detector.find_element_robust(selectors)
        
        assert element is not None
        assert detector.extract_text_safe(element) == "Click Me"
        assert detector.is_element_present(By.ID, "test-btn")
    
    @pytest.mark.slow
    def test_real_wait_for_element(self, real_browser_manager, browser_available):
        """Test waiting for element with real browser"""
        if not browser_available:
            pytest.skip("Browser not available")
        
        driver = real_browser_manager.get_driver()
        detector = ElementDetector(driver)
        
        # Navigate to page with delayed element
        html = """
        <html><body>
        <script>
        setTimeout(function() {
            var btn = document.createElement('button');
            btn.id = 'delayed-btn';
            btn.textContent = 'Delayed Button';
            document.body.appendChild(btn);
        }, 1000);
        </script>
        </body></html>
        """
        driver.get(f"data:text/html,{html}")
        
        # Wait for element to appear
        element = detector.wait_for_element(By.ID, "delayed-btn", timeout=3)
        
        assert element is not None
        assert detector.extract_text_safe(element) == "Delayed Button"