from . import CrawlerModule
from .utils.logger import Logger
import time
from datetime import datetime

class IADFranceModule(CrawlerModule):

    def __init__(self):
        super().__init__("IADFrance", "This is a module for iadfrance.fr", True, False)
        self.logger = Logger(self.name)
        self.base_url = "https://www.iadfrance.fr"
        self.logger.success('Module loaded.')

        self.set_random_proxy()

        self.tls_session.client_identifier = "chrome_137"
        self.tls_session.random_tls_extension_order = True
        self.tls_session.headers.update({
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "accept": "application/json, text/plain, */*",
            "accept-language": "fr-FR,fr;q=0.9,en;q=0.8",
            "referer": "https://www.iadfrance.fr/",
        })

    def getAds(self, page: int = 1, pageSize: int = 100):
        try:
            params = {
                'serpSlug': 'vente',
                'locale': 'fr',
                'page': page,
                'itemsPerPage': pageSize
            }
            
            url = f'{self.base_url}/api/properties'
            resp = self.tls_session.get(url, params=params)

            if resp.status_code == 200:
                data = resp.json()
                return data
            else:
                self.logger.error(f"HTTP Error: {resp.status_code}")
                return False
            
        except Exception as e:
            self.logger.error(f"Error fetching ads: {str(e)}")
            return False

    def normalize_and_save_ads(self, ads_data):
        if not ads_data or 'items' not in ads_data:
            self.logger.warning("No ads data found in response")
            return 0
        
        ads = ads_data.get('items', [])
        saved_count = 0
        
        for ad in ads:
            try:
                photos = ad.get('photos', [])
                
                property_type_mapping = {
                    'house': 'maison',
                    'apartment': 'appartement',
                    'land': 'terrain',
                    'parking': 'parking',
                    'business': 'local commercial',
                    'building': 'immeuble'
                }
                
                property_type = property_type_mapping.get(
                    ad.get('propertyType', ''), 
                    ad.get('propertyDisplayType', ad.get('propertyType', ''))
                )

                location = ad.get('location', {})
                surfaces = ad.get('surfaces', [])
                rooms = ad.get('rooms', [])
                prices = ad.get('prices', {})
                agent = ad.get('agent', {})
                
                living_area = None
                plot_area = None
                for surface in surfaces:
                    if surface.get('type') == 'living-area':
                        living_area = surface.get('value')
                    elif surface.get('type') == 'plot-area':
                        plot_area = surface.get('value')
                
                room_count = None
                for room in rooms:
                    if room.get('type') == 'rooms':
                        room_count = room.get('value')
                
                property_ref = ad.get('propertyListingRef')
                slug = ad.get('slugs', {}).get('fr', '')
                
                url = f"https://www.iadfrance.fr/annonce/{slug}/r{property_ref}" if slug else None
                
                normalized = self.normalize_ad(
                    id=property_ref,
                    source="iadfrance",
                    url=url,
                    title=f"{property_type.capitalize()} {room_count or '?'} pièce(s) {living_area or '?'} m²",
                    description=ad.get('description', ''),
                    property_type=property_type,
                    transaction_type='vente',
                    price=prices.get('main'),
                    city=location.get('place'),
                    postal_code=location.get('postcode'),
                    surface=living_area,
                    rooms=room_count,
                    bedrooms=None,
                    photos=photos,
                    agency_name=agent.get('fullName'),
                    agency_phone=None,
                    created_at=None,
                    updated_at=None,
                )
                
                self._shared_db.get_collection("ads").update_one(
                    {"id": normalized["id"]},
                    {"$set": normalized},
                    upsert=True
                )
                
                saved_count += 1
                
            except Exception as e:
                self.logger.error(f"Error normalizing ad {ad.get('propertyListingRef', 'unknown')}: {str(e)}")
                continue
        return saved_count
    
    def start(self):
        if not self.enabled:
            raise Exception("This module is currently disabled.")

        page = 1
        page_size = 100
        total_saved = 0
        
        while True:
            self.logger.info(f"Fetching listings from IAD France... (Page {page})")

            response = self.getAds(page=page, pageSize=page_size)
            
            if response is False:
                self.logger.warning('Error while fetching data, switching proxy, waiting 5s before retrying...')
                self.set_random_proxy()
                time.sleep(5)
                continue
            
            total_items = response.get('totalItems', 0)
            if total_items > self.total_ads_found:
                self.total_ads_found = total_items
                
            self.logger.info(f"Total ads available: {total_items}")
            
            items = response.get('items', [])

            # if not items:
            #     self.logger.info("No more ads found, stopping...")
            #     break
            
            ads_count = len(items)
            self.logger.info(f"Found {ads_count} ads on page {page}")
            
            saved_count = self.normalize_and_save_ads(response)
            total_saved += saved_count
            
            self.logger.success(f"Page {page}: Processed and saved {saved_count} ads to database")
            self.current_scrapped_ads += saved_count
            
            if ads_count < page_size:
                self.logger.info("Reached end of listings")
                break
            
            if total_saved >= total_items and total_saved > 0  :
                self.logger.info("All available ads have been processed")
                break
            
            page += 1
        
        self.logger.success(f"Finished! Total ads saved: {total_saved}")
        