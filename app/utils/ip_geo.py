"""
IP Geolocation Utility
"""
import geoip2.database
from typing import Optional


class IPGeoLocator:
    """IP geolocation service"""

    def __init__(self, db_path: str = "data/geoip/GeoLite2-City.mmdb"):
        self.db_path = db_path
        self.reader: Optional[geoip2.database.Reader] = None

    def _get_reader(self) -> geoip2.database.Reader:
        """Get GeoIP reader"""
        if self.reader is None:
            self.reader = geoip2.database.Reader(self.db_path)
        return self.reader

    def lookup(self, ip_address: str) -> dict:
        """Look up IP address location"""
        # Implementation to be added
        pass

    def is_vpn_or_proxy(self, ip_address: str) -> bool:
        """Check if IP is VPN or proxy"""
        # Implementation to be added
        pass
