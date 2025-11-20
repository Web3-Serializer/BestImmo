from . import CrawlerModule
from .utils.logger import Logger
import time
from datetime import datetime

class BienIciModule(CrawlerModule):

    def __init__(self):
        super().__init__("BienIci", "This is a module for bienici.com", True, False)
        self.logger = Logger(self.name)
        self.base_url = "https://www.bienici.com/"
        self.logger.success('Module loaded.')

        self.set_random_proxy()

        self.tls_session.client_identifier = "chrome_137"
        self.tls_session.random_tls_extension_order = True
        self.tls_session.headers.update({
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "accept": "*/*",
            "referer": f"https://www.bienici.com/",
        })

    def getAds(self, page: int=1, pageSize: int=24):
        try:
            from_param = (page - 1) * pageSize
            
            resp = self.tls_session.get(
                f'{self.base_url}realEstateAds.json?filters=%7B"size"%3A{pageSize}%2C"from"%3A{from_param}%2C"showAllModels"%3Afalse%2C"filterType"%3A"buy"%2C"propertyType"%3A%5B"house"%2C"flat"%2C"loft"%2C"castle"%2C"townhouse"%5D%2C"page"%3A{page}%2C"sortBy"%3A"relevance"%2C"sortOrder"%3A"desc"%2C"onTheMarket"%3A%5Btrue%5D%2C"mapMode"%3A"enabled"%7D&extensionType=extendedIfNoResult&enableGoogleStructuredDataAggregates=true&leadingCount=2'
            )

            if resp.status_code == 200:
                data = resp.json()
                if not data.get('success', True):
                    self.logger.error(f"API Error: {data.get('errorMessage', 'Unknown error')}")
                    return False
                return data
            else:
                self.logger.error(f"HTTP Error: {resp.status_code}")
                return False
        except Exception as e:
            self.logger.error(f"Error fetching ads: {str(e)}")
            return False

    def normalize_and_save_ads(self, ads_data):
        if not ads_data or 'realEstateAds' not in ads_data:
            self.logger.warning("No ads data found in response")
            return 0
        
        
        ads = ads_data.get('realEstateAds', [])
        saved_count = 0
        
        for ad in ads:
            try:
                photos = []
                if ad.get('photos'):
                    photos = [photo.get('url', '') for photo in ad.get('photos', []) if photo.get('url')]
                
                created_at = None
                updated_at = None
                
                if ad.get('publicationDate'):
                    try:
                        created_at = datetime.fromisoformat(ad.get('publicationDate').replace('Z', '+00:00'))
                    except:
                        pass
                        
                if ad.get('modificationDate'):
                    try:
                        updated_at = datetime.fromisoformat(ad.get('modificationDate').replace('Z', '+00:00'))
                    except:
                        pass

                property_type_mapping = {
                    'house': 'maison',
                    'flat': 'appartement',
                    'loft': 'loft',
                    'castle': 'château',
                    'townhouse': 'maison de ville'
                }
                property_type = property_type_mapping.get(ad.get('propertyType', ''), ad.get('propertyType', ''))

                transaction_type = 'vente' if ad.get('adType') == 'buy' else ad.get('adType', '')

                normalized = self.normalize_ad(
                    id=ad.get('id'),
                    source="bienici",
                    url=f"https://www.bienici.com/annonce/{ad.get('id')}" if ad.get('id') else None,
                    title=ad.get('title'),
                    description=ad.get('description'),
                    property_type=property_type,
                    transaction_type=transaction_type,
                    price=ad.get('price'),
                    city=ad.get('city'),
                    postal_code=ad.get('postalCode'),
                    surface=ad.get('surfaceArea'),
                    rooms=ad.get('roomsQuantity'),
                    bedrooms=ad.get('bedroomsQuantity'),
                    photos=photos,
                    agency_name=ad.get('accountDisplayName'),
                    agency_phone=None,
                    created_at=created_at,
                    updated_at=updated_at,
                )
                
                self._shared_db.get_collection("ads").update_one(
                    {"id": normalized["id"]},
                    {"$set": normalized},
                    upsert=True
                )
                
                saved_count += 1
                
            except Exception as e:
                self.logger.error(f"Error normalizing ad {ad.get('id', 'unknown')}: {str(e)}")
                continue
        
        return saved_count
    
    def start(self):
        if not self.enabled:
            raise Exception("This module is currently disabled.")

        page = 1
        page_size = 24
        max_pages = 999999
        
        while True:
            self.logger.info(f"Fetching listings from BienICI... (Page {page})")

            response = self.getAds(page=page, pageSize=page_size)

            if response == False:
                self.logger.warning('Error while fetching data, switching proxy, waiting 5s before retrying...')
                self.set_random_proxy()
                time.sleep(5)
                continue

            total = response.get('total', 0)
            max_pages = response.get('total', 0) / page_size

            if total > self.total_ads_found: self.total_ads_found = total
            self.logger.info(f"Total ads to fetch: {total}")
     
            ads_count = len(response.get('realEstateAds', []))
            self.logger.info(f"Found {ads_count} ads on page {page}")
            
            saved_count = self.normalize_and_save_ads(response)
            self.logger.success(f"Page {page}: Processed and saved {saved_count} ads to database")
            self.current_scrapped_ads += saved_count
            
            if ads_count < page_size or page >= max_pages:
                if page >= max_pages:
                    self.logger.info(f"Reached maximum pages limit ({max_pages})")
                else:
                    self.logger.info("Reached end of listings")
                break
            
            page += 1
        
        self.logger.success(f"Finished! Total ads saved: {self.current_scrapped_ads}")