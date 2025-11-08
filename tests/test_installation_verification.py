"""
Simple test to verify all dependencies are installed correctly
"""

def test_basic_imports():
    """Test that core dependencies can be imported"""
    
    print("Testing basic dependency imports...")
    
    # Test core dependencies
    try:
        import requests
        print("✅ requests imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import requests: {e}")
        return False
    
    try:
        import pydantic
        print("✅ pydantic imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import pydantic: {e}")
        return False
    
    try:
        import selenium
        print("✅ selenium imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import selenium: {e}")
        return False
    
    try:
        import psutil
        print("✅ psutil imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import psutil: {e}")
        return False
    
    try:
        import cryptography
        print("✅ cryptography imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import cryptography: {e}")
        return False
    
    # Test Plus500US core client
    try:
        from plus500us_client.requests import AuthClient
        print("✅ Plus500US requests module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import Plus500US requests module: {e}")
        return False
    
    try:
        from plus500us_client.requests.config import load_config, Config
        config = load_config()
        print(f"✅ Plus500US config loaded successfully: {type(config)}")
    except ImportError as e:
        print(f"❌ Failed to import Plus500US config: {e}")
        return False
    
    print("\n🎉 All dependency tests passed successfully!")
    return True

def test_basic_functionality():
    """Test basic Plus500US client functionality without WebDriver"""
    
    print("\nTesting basic Plus500US functionality...")
    
    try:
        from plus500us_client.requests import AuthClient
        from plus500us_client.requests.config import load_config
        
        # Load configuration
        config = load_config()
        print(f"✅ Configuration loaded: account_type={config.account_type}")
        
        # Initialize authentication client (skip initialization, just test import)
        print("✅ AuthClient imported successfully")
        
        # Test model creation
        from plus500us_client.requests.models import OrderDraft, Instrument
        
        # Create a test order draft
        order = OrderDraft(
            instrument_id="TEST123",
            side="BUY",
            order_type="MARKET",
            qty=1.0
        )
        print(f"✅ OrderDraft model created: {order.instrument_id}")
        
        # Create a test instrument
        instrument = Instrument(
            id="TEST123",
            symbol="TEST",
            name="Test Instrument"
        )
        print(f"✅ Instrument model created: {instrument.symbol}")
        
        print("✅ All basic functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Basic functionality test failed: {e}")
        return False

if __name__ == "__main__":
    print("=== Plus500US Dependency & Installation Verification ===\n")
    
    if test_basic_imports() and test_basic_functionality():
        print("\n🚀 Installation verification complete - Everything is working!")
        exit(0)
    else:
        print("\n💥 Installation verification failed - Some issues detected")
        exit(1)