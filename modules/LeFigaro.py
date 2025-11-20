# Imports

from . import CrawlerModule # Super class for Module
import urllib.parse
from .utils.logger import Logger
import time

# Crawler

class LeFigaroModule(CrawlerModule):

    def __init__(self):
        super().__init__("LeFigaro", "This is a module for immobilier.lefigaro.fr", True, False)
        self.logger = Logger(self.name)
        self.base_url = "https://immobilier.lefigaro.fr"
        self.logger.success('Module loaded.')

        self.set_random_proxy()

        # TLS session config
        self.tls_session.client_identifier = "chrome_137"
        self.tls_session.random_tls_extension_order = True
        self.tls_session.headers.update({
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "referer": f"https://immobilier.lefigaro.fr/",
            "sec-ch-ua": '"Not.A/Brand";v="8", "Chromium";v="137", "Google Chrome";v="137"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-full-version": '"137.0.7151.120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-platform-version": '"10.0.0"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-api-key": "AIzaSyDb4PeV9gi5UY_Z3-27ygjOm8PV950j9Us"
        })



    def getAds(self, query: str, page: int=1, pageSize: int=31):
        try:
            query = urllib.parse.quote(query)
            resp = self.tls_session.get(
                f"{self.base_url}/web/classifieds?location={query}&transaction=vente&path=/annonces/immobilier-vente-bien-france.html&currentPage={page}&pageSize={pageSize}"
            )

            return resp.json()
        except:
            return False
    
    def start(self):
        if not self.enabled:
            raise Exception("This module is currently disabled.")

        while True:
            self.logger.info("Fetching listings from LeFigaro...")

            page = 1
            page_size = 30

            first_response = self.getAds('France', page=page, pageSize=page_size)
            
            if first_response == False:
                self.logger.warning('Error while fetching data, switching proxy, waiting 5s before restarting...')
                self.set_random_proxy()
                time.sleep(5)
            else:
                break
        
        total = first_response.get("total", 0)
        self.total_ads_found = total

        classifieds = first_response.get("classifieds", [])
        
        self.logger.info(f"Total ads to fetch: {total}")
        
        self._process_ads(classifieds, page)

        total_pages = 100 # max

        for p in range(page+1, total_pages + 1):
            self.logger.info(f"Fetching page {p} of {total_pages}...")
            try:
                response = self.getAds('France', page=p, pageSize=page_size)
                if isinstance(response, dict):
                    classifieds = response.get("classifieds", [])
                    self._process_ads(classifieds, p)
            except Exception as e:
                self.logger.error(f"Error fetching page {p}: {e}")
                continue

        self.logger.success("All ads have been normalized and saved to the database.")


    def _process_ads(self, ads, page_num):
        """Process and save ads from a single page"""
        if not isinstance(ads, list):
            return
        
        processed_count = 0
        
        for ad in ads:
            if not isinstance(ad, dict):
                continue
                
            try:
                photos = []
                images = ad.get('images', {})
                if isinstance(images, dict):
                    photos_data = images.get('photos', [])
                    if isinstance(photos_data, list):
                        photos = [photo.get('url', {}).get('medium') for photo in photos_data 
                                    if isinstance(photo, dict) and photo.get('url', {}).get('medium')]

                room_count = ad.get('roomCount', [])
                rooms = room_count[0] if isinstance(room_count, list) and room_count else None

                normalized = self.normalize_ad(
                    id=ad.get('id'),
                    source="lefigaro",
                    url=ad.get('recordLink'),
                    title=f"{str(ad.get('transaction')).capitalize()} {ad.get('type')} {ad.get('roomCountLabel') or ''} {int(ad.get('area')) or '?'} m²",
                    description=ad.get('description'),
                    property_type=ad.get('type'),
                    transaction_type=ad.get('transaction'),
                    price=ad.get('price'),
                    city=ad.get('location', {}).get('city'),
                    postal_code=ad.get('location', {}).get('postalCode'),
                    surface=ad.get('area'),
                    rooms=rooms,
                    bedrooms=ad.get('bedRoomCount'),
                    photos=photos,
                    agency_name=ad.get('client', {}).get('brandName'),
                    agency_phone=ad.get('client', {}).get('phoneNumber'),
                    created_at=ad.get('creationDate'),
                    updated_at=ad.get('updatedAt'),
                )
                
                self._shared_db.get_collection("ads").update_one(
                    {"id": normalized["id"]},
                    {"$set": normalized},
                    upsert=True
                )
                
                processed_count += 1
                
            except Exception as e:
                self.logger.error(f"Error normalizing ad {ad.get('id', 'unknown')}: {e}")
                continue
        
        self.logger.success(f"Page {page_num}: Processed and saved {processed_count} ads to database")
        self.current_scrapped_ads += processed_count 
