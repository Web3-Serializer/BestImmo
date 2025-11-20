import tls_client, random
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

from .utils.db import MongoDB
from .utils.logger import Logger
from .utils import proxy

class CrawlerModule:

    _logger = Logger('Crawler')
    _shared_db = None

    def __init__(self, name: str, description: str, enabled: bool, proxyless: bool):
        self.tls_session = tls_client.Session()
        self.name = name
        self.desc = description
        self.enabled = enabled
        self.proxyless = proxyless
        
        self.current_scrapped_ads = 0
        self.total_ads_found = 0
        self.current_proxy = None

        if CrawlerModule._shared_db is None:
            CrawlerModule._shared_db = MongoDB()
            try:
                CrawlerModule._shared_db.connect()
            except Exception as e:
                CrawlerModule._logger.error(f"DB connection error: {e}")

    def set_random_proxy(self):
        self.current_proxy = random.choice(proxy.load_proxies())
        self.tls_session.proxies.update({
            "http": f"http://{self.current_proxy}",
            "https": f"http://{self.current_proxy}"
        })
        self._logger.info(f'Proxy has been set to : {self.current_proxy}')

    def normalize_ad(
        self,
        # Core identifiers
        id: str,
        source: str,
        url: Optional[str] = None,
        
        # Basic info
        title: Optional[str] = None,
        description: Optional[str] = None,
        property_type: Optional[str] = None,
        transaction_type: Optional[str] = None,
        
        # Price
        price: Optional[Union[int, float]] = None,
        currency: str = "EUR",
        
        # Location
        city: Optional[str] = None,
        postal_code: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        
        # Property details
        surface: Optional[Union[int, float]] = None,
        rooms: Optional[int] = None,
        bedrooms: Optional[int] = None,
        
        # Media
        photos: Optional[List[str]] = None,
        
        # Contact
        agency_name: Optional[str] = None,
        agency_phone: Optional[str] = None,
        
        # Timestamps
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        
        # Extra fields
        **extra_fields
    ) -> Dict[str, Any]:
        """
        Normalize property ad data into a simple, consistent structure.
        
        Args:
            id: Unique identifier for the ad
            source: Source provider (e.g., 'seloger', 'figaro', 'leboncoin')
            url: URL to the original ad
            title: Ad title
            description: Ad description
            property_type: Type of property (apartment, house, etc.)
            transaction_type: Type of transaction (sale, rental)
            price: Price in specified currency
            currency: Currency code (default: EUR)
            city: City name
            postal_code: Postal code
            latitude: GPS latitude
            longitude: GPS longitude
            surface: Surface area in m²
            rooms: Total number of rooms
            bedrooms: Number of bedrooms
            photos: List of photo URLs
            agency_name: Agency or contact name
            agency_phone: Phone number
            created_at: Creation timestamp
            updated_at: Last update timestamp
            **extra_fields: Any additional fields
        
        Returns:
            Dict: Normalized ad data
        """
        
        def clean_value(value):
            if value is None:
                return None
            if isinstance(value, str):
                return value.strip() if value.strip() else None
            return value
        
        def clean_numeric(value):
            if value is None:
                return None
            try:
                return float(value) if isinstance(value, str) else value
            except (ValueError, TypeError):
                return None
        
        normalized = {
            "id": str(id),
            "source": source,
            "url": clean_value(url),
            "title": clean_value(title),
            "description": clean_value(description),
            "property_type": clean_value(property_type),
            "transaction_type": clean_value(transaction_type),
            "price": clean_numeric(price),
            "currency": currency,
            "city": clean_value(city),
            "postal_code": clean_value(postal_code),
            "latitude": clean_numeric(latitude),
            "longitude": clean_numeric(longitude),
            "surface": clean_numeric(surface),
            "rooms": clean_numeric(rooms),
            "bedrooms": clean_numeric(bedrooms),
            "photos": photos or [],
            "agency_name": clean_value(agency_name),
            "agency_phone": clean_value(agency_phone),
            "created_at": created_at,
            "updated_at": updated_at,
            "retrieved_at": datetime.utcnow().isoformat()
        }
        
        normalized = {k: v for k, v in normalized.items() if v is not None}
        
        if extra_fields:
            normalized.update(extra_fields)
        
        return normalized



