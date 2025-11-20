# Imports

from . import CrawlerModule
import json, time
from .utils.logger import Logger
from datetime import datetime


# Crawler

class LogicImmoModule(CrawlerModule):

    def __init__(self):
        super().__init__("LogicImmo", "Module for logic-immo.com property listings", True, False)
        self.logger = Logger(self.name)
        self.base_url = "https://www.logic-immo.com"
        self.logger.success("Module loaded.")

        self.set_random_proxy()

        # TLS session config
        self.tls_session.client_identifier = "chrome_137"
        self.tls_session.random_tls_extension_order = True
        self.tls_session.headers.update({
            "host": "www.logic-immo.com",
            "connection": "keep-alive",
            "sec-ch-ua-platform": "\"Windows\"",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "sec-ch-ua": "\"Google Chrome\";v=\"137\", \"Chromium\";v=\"137\", \"Not/A)Brand\";v=\"24\"",
            "content-type": "application/json; charset=utf-8",
            "sec-ch-ua-mobile": "?0",
            "accept": "*/*",
            "origin": "https://www.logic-immo.com/",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
            "referer": f"https://www.logic-immo.com/",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
            "x-language": "fr"
        })

    def getAdsIds(self, place_id: str = "AD02FR1", page: int = 1, pageSize: int = 25):
        try:
            url = f"{self.base_url}/serp-bff/search"

            payload = {
                "criteria": {
                    "distributionTypes": ["Buy", "Buy_Auction", "Compulsory_Auction"],
                    "estateTypes": ["House", "Apartment"],
                    "location": {"placeIds": [place_id]}
                },
                "paging": {
                    "page": page,
                    "size": pageSize,
                    "order": "Default"
                }
            }

            response = self.tls_session.post(
                url,
                json=payload
            )

            return response.json()
        except:
            return False
    
    def getAdsById(self, ids: list):
        try:
            list_arg = ",".join(ids)
            response = self.tls_session.get(f'{self.base_url}/classifiedList/{list_arg}')
            return response.json()
        except:
            return False
        
    def _switch_proxy(self):
        self.logger.warning('Error while fetching data, switching proxy, waiting 5s before restarting...')
        self.set_random_proxy()
        time.sleep(5)

    def start(self):
        if not self.enabled:
            raise Exception("This module is currently disabled.")
        
        while True:
            self.logger.info("Fetching listings from LogicImmo...")

            place_id = "AD02FR1"
            page = 1
            pageSize = 25

            first_response = self.getAdsIds(place_id=place_id, page=page, pageSize=pageSize)

            if first_response == False:
                self._switch_proxy()
            else:
                break

        total = first_response.get("totalCount", 0)
        self.total_ads_found = total

        classifieds = first_response.get("classifieds", [])
        page_1_ids = [ad.get('id') for ad in classifieds if isinstance(ad, dict) and ad.get('id')]

        self.logger.info(f"Total ads to fetch: {total}")

        self._process_ads(page_1_ids, page)

        total_pages = (total + pageSize - 1) // pageSize

        for p in range(2, total_pages + 1):
            self.logger.info(f"Fetching page {p} of {total_pages}...")
            response = self.getAdsIds(place_id=place_id, page=p, pageSize=pageSize)

            if isinstance(response, dict):
                classifieds = response.get("classifieds", [])
                page_ids = [ad.get('id') for ad in classifieds if isinstance(ad, dict) and ad.get('id')]
            
                self._process_ads(page_ids, p)
            else:
                self._switch_proxy()

        self.logger.success("All ads have been normalized and saved to the database.")

    def _process_ads(self, ad_ids, page_num):
        if not ad_ids:
            return
        
        self.logger.info(f"Processing {len(ad_ids)} ads from page {page_num}...")
        
        chunk_size = 50
        processed_count = 0
        
        for i in range(0, len(ad_ids), chunk_size):
            chunk = ad_ids[i:i+chunk_size]
            self.logger.info(f"Page {page_num}: Fetching details for ads {i + 1} to {i + len(chunk)}...")
            
            try:
                ads_data = self.getAdsById(chunk)
                if isinstance(ads_data, list):
                    ads_list = [ad for ad in ads_data if isinstance(ad, dict)]
                elif isinstance(ads_data, dict) and ads_data.get("classifieds"):
                    ads_list = [ad for ad in ads_data.get("classifieds", []) if isinstance(ad, dict)]
                else:
                    continue
                
                for ad in ads_list:
                    try:
                        photos = []
                        gallery = ad.get('gallery', {})
                        if isinstance(gallery, dict):
                            images = gallery.get('images', [])
                            if isinstance(images, list):
                                photos = [img.get('url') for img in images if isinstance(img, dict) and img.get('url')]

                        phone_numbers = ad.get('provider', {}).get('phoneNumbers', [])
                        agency_phone = phone_numbers[0] if isinstance(phone_numbers, list) and phone_numbers else None

                        normalized = self.normalize_ad(
                            id=ad.get('id'),
                            source="logic-immo",
                            url=ad.get('url'),
                            title=ad.get('mainDescription', {}).get('headline'),
                            description=ad.get('mainDescription', {}).get('description'),
                            property_type=ad.get('rawData', {}).get('propertyType'),
                            transaction_type=ad.get('rawData', {}).get('distributionType'),
                            price=ad.get('tracking', {}).get('price') or ad.get('rawData', {}).get('price'),
                            city=ad.get('location', {}).get('address', {}).get('city'),
                            postal_code=ad.get('location', {}).get('address', {}).get('zipCode'),
                            surface=ad.get('rawData', {}).get('surface', {}).get('main') if ad.get('rawData', {}).get('surface') else None,
                            rooms=ad.get('rawData', {}).get('nbroom'),
                            bedrooms=ad.get('rawData', {}).get('nbbedroom'),
                            photos=photos,
                            agency_name=ad.get('provider', {}).get('intermediaryCard', {}).get('title'),
                            agency_phone=agency_phone,
                            created_at=ad.get('metadata', {}).get('creationDate'),
                            updated_at=ad.get('metadata', {}).get('updateDate'),
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
                        
            except Exception as e:
                self.logger.error(f"Error fetching chunk from page {page_num}: {e}")
                continue
        
        self.logger.success(f"Page {page_num}: Processed and saved {processed_count} ads to database")
        self.current_scrapped_ads += processed_count