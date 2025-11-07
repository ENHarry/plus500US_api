from __future__ import annotations
from typing import Dict, Any, List
from .config import Config
from .session import SessionManager
from .account import AccountClient
from .instruments import InstrumentsClient
from .models import Account, Instrument

class PostLoginDataService:
    """Service to retrieve comprehensive account and instrument data after login"""
    
    def __init__(self, cfg: Config, sm: SessionManager):
        self.cfg = cfg
        self.sm = sm
        self.account_client = AccountClient(cfg, sm)
        self.instruments_client = InstrumentsClient(cfg, sm)
    
    def retrieve_all_data(self) -> Dict[str, Any]:
        """Retrieve all post-login data: account info, instruments, and trading parameters"""
        data = {}
        
        try:
            # Get enhanced account information
            data["account"] = self._get_enhanced_account_info()
            
            # Get all tradable instruments with full metadata
            data["instruments"] = self._get_enhanced_instruments()
            
            # Update config with instrument metadata
            self._update_config_metadata(data["instruments"])
            
            # Get trading parameters and limits
            data["trading_limits"] = self._get_trading_limits()
            
            print(f"✓ Retrieved account information (Account Type: {data['account'].account_type})")
            print(f"✓ Retrieved {len(data['instruments'])} tradable instruments")
            print(f"✓ Account Balance: ${data['account'].balance:,.2f}")
            print(f"✓ Available Funds: ${data['account'].available:,.2f}")
            
        except Exception as e:
            print(f"⚠ Warning: Could not retrieve some post-login data: {e}")
            # Return partial data even if some calls fail
            data.setdefault("account", None)
            data.setdefault("instruments", [])
            data.setdefault("trading_limits", {})
        
        return data
    
    def _get_enhanced_account_info(self) -> Account:
        """Get detailed account information including commission rates and limits"""
        account = self.account_client.get_account()
        
        # Try to get additional account details if available
        try:
            s = self.sm.session
            host = self.cfg.host_url
            
            # Get commission and fee information
            r = s.get(host + "/ClientRequest/GetAccountDetails", timeout=15)
            if r.status_code == 200:
                details = r.json()
                
                # Update account with additional information
                if "commission_per_contract" in details:
                    account.commission_per_contract = details["commission_per_contract"]
                if "commission_percentage" in details:
                    account.commission_percentage = details["commission_percentage"]
                if "overnight_fee_rate" in details:
                    account.overnight_fee_rate = details["overnight_fee_rate"]
                if "max_position_value" in details:
                    account.max_position_value = details["max_position_value"]
                    
        except Exception:
            # Continue with basic account info if enhanced details fail
            pass
            
        return account
    
    def _get_enhanced_instruments(self) -> List[Instrument]:
        """Get all instruments with enhanced metadata including commission and margin info"""
        instruments = self.instruments_client.list_instruments()
        
        # Try to enhance each instrument with additional metadata
        enhanced_instruments = []
        for instrument in instruments:
            try:
                enhanced = self._enhance_instrument_metadata(instrument)
                enhanced_instruments.append(enhanced)
            except Exception:
                # Use basic instrument data if enhancement fails
                enhanced_instruments.append(instrument)
                
        return enhanced_instruments
    
    def _enhance_instrument_metadata(self, instrument: Instrument) -> Instrument:
        """Enhance instrument with commission, margin, and trading metadata"""
        try:
            s = self.sm.session
            host = self.cfg.host_url
            
            # Get detailed instrument information
            r = s.get(host + f"/ClientRequest/GetInstrumentDetails/{instrument.id}", timeout=10)
            if r.status_code == 200:
                details = r.json()
                
                # Update instrument with enhanced metadata
                if "commission_rate" in details:
                    instrument.commission_rate = details["commission_rate"]
                if "commission_min" in details:
                    instrument.commission_min = details["commission_min"]
                if "overnight_fee_long" in details:
                    instrument.overnight_fee_long = details["overnight_fee_long"]
                if "overnight_fee_short" in details:
                    instrument.overnight_fee_short = details["overnight_fee_short"]
                if "initial_margin" in details:
                    instrument.initial_margin = details["initial_margin"]
                if "maintenance_margin" in details:
                    instrument.maintenance_margin = details["maintenance_margin"]
                if "max_position_size" in details:
                    instrument.max_position_size = details["max_position_size"]
                if "spread_typical" in details:
                    instrument.spread_typical = details["spread_typical"]
                if "trading_hours_start" in details:
                    instrument.trading_hours_start = details["trading_hours_start"]
                if "trading_hours_end" in details:
                    instrument.trading_hours_end = details["trading_hours_end"]
                    
        except Exception:
            # Return basic instrument if enhancement fails
            pass
            
        return instrument
    
    def _update_config_metadata(self, instruments: List[Instrument]) -> None:
        """Update config futures_metadata with instrument data"""
        metadata = {}
        
        for instrument in instruments:
            root = instrument.root or instrument.symbol.split()[0]
            metadata[root] = {
                "tick_size": instrument.tick_size or 0.25,
                "min_qty": instrument.min_qty or 1.0,
                "tick_value": instrument.tick_value or 0.25,
                "commission_rate": float(instrument.commission_rate or 0),
                "initial_margin": float(instrument.initial_margin or 0),
                "maintenance_margin": float(instrument.maintenance_margin or 0),
            }
        
        # Update config
        self.cfg.futures_metadata.update(metadata)
    
    def _get_trading_limits(self) -> Dict[str, Any]:
        """Get trading limits and parameters"""
        limits = {
            "max_orders_per_minute": self.cfg.max_requests_per_minute,
            "poll_interval_ms": self.cfg.poll_interval_ms,
            "account_type": self.cfg.account_type
        }
        
        try:
            s = self.sm.session
            host = self.cfg.host_url
            
            # Get additional trading limits
            r = s.get(host + "/ClientRequest/GetTradingLimits", timeout=10)
            if r.status_code == 200:
                additional_limits = r.json()
                limits.update(additional_limits)
                
        except Exception:
            # Use default limits if API call fails
            pass
            
        return limits