def find_element_from_selector(self, selector_dict: Dict[str, List[str]], 
                                   timeout: Optional[int] = None) -> Optional[WebElement]:
        """Find and return WebElement from selector dictionary"""
        return self.find_element_robust(selector_dict, timeout)